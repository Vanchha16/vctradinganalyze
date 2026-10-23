"""Unit tests for the hourly signal-generation task's confirmation gate
(`_has_open_signal`) - mirrors `test_signal_monitoring_tasks.py`'s
in-memory SQLite session-factory pattern. Doesn't exercise
`generate_signals_task` end-to-end (that would require standing up the
full AI orchestration dependency graph); the AI/telegram side is already
covered by `test_signal_engine.py` and `test_telegram_tasks.py`."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from celery.schedules import crontab
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, Recommendation, SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.repositories.signal_repository import SignalRepository
from app.services.signal_engine import SignalGenerationResult
from app.workers.signal_tasks import (
    OPEN_SIGNAL_NOTE,
    _has_open_signal,
    _process_asset,
    register_signal_schedule,
)

_TABLES = [Asset.__table__, AIAnalysis.__table__, Signal.__table__]


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    yield sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def _seed_signal(
    session: Session,
    *,
    status: SignalStatus = SignalStatus.ACTIVE,
    created_at: datetime | None = None,
) -> Asset:
    asset = Asset(symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX)
    session.add(asset)
    session.flush()

    analysis = AIAnalysis(
        asset_id=asset.id,
        timeframe=Timeframe.H1,
        recommendation=Recommendation.BUY,
        confidence_score=80.0,
        confidence_level="high",
        reasoning={},
        supporting_evidence=[],
        model_name="mock",
        prompt_version="1.0.0",
    )
    session.add(analysis)
    session.flush()

    signal = Signal(
        analysis_id=analysis.id,
        asset_id=asset.id,
        timeframe=Timeframe.H1,
        signal_type=SignalType.BUY,
        entry_price="100",
        stop_loss="95",
        take_profit="115",
        risk_reward=3.0,
        confidence=80.0,
        status=status,
    )
    session.add(signal)
    session.flush()
    if created_at is not None:
        signal.created_at = created_at
    session.commit()
    return asset


def test_has_open_signal_false_for_an_unfilled_active_signal_while_confirmation_is_on(
    session_factory: sessionmaker[Session],
) -> None:
    """ADR-168 - a newer setup may be drafted and, once confirmed, replace
    the unfilled signal; blocking here would lose that confirmation."""
    with session_factory() as session:
        asset = _seed_signal(session)
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is False


def test_has_open_signal_true_for_active_unexpired_signal_without_confirmation(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With confirmation off there is no replacement step - a new signal
    would be published beside the open one - so ACTIVE still blocks."""
    monkeypatch.setattr(settings, "signal_confirmation_enabled", False)
    with session_factory() as session:
        asset = _seed_signal(session)
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is True


def test_has_open_signal_false_when_no_signal_exists(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL)
        session.add(asset)
        session.commit()
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is False


def test_has_open_signal_false_once_ttl_expired(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stored-ACTIVE signal past `signal_ttl_hours` is EXPIRED at
    read-time (ADR-088) - the hourly job must be free to generate a new
    call for the asset once that happens. Confirmation off, the only case
    where ACTIVE blocks at all (ADR-168)."""
    monkeypatch.setattr(settings, "signal_confirmation_enabled", False)
    stale_created_at = datetime.now(UTC) - timedelta(hours=48)
    with session_factory() as session:
        asset = _seed_signal(session, created_at=stale_created_at)
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is False


def test_has_open_signal_false_for_closed_signal(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        asset = _seed_signal(session, status=SignalStatus.SUCCESSFUL)
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is False


def test_has_open_signal_true_for_triggered_signal(
    session_factory: sessionmaker[Session],
) -> None:
    """ADR-137: a TRIGGERED signal is a live trade, more open than a
    pending ACTIVE one - it must also block regeneration."""
    with session_factory() as session:
        asset = _seed_signal(session, status=SignalStatus.TRIGGERED)
        signal = session.query(Signal).filter(Signal.asset_id == asset.id).one()
        signal.triggered_at = datetime.now(UTC)
        session.commit()
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is True


def test_has_open_signal_false_once_triggered_ttl_elapsed(
    session_factory: sessionmaker[Session],
) -> None:
    """Once a TRIGGERED signal is effectively CLOSED by
    `signal_triggered_ttl_hours` (ADR-137 §3.4), it must stop blocking
    regeneration for that asset."""
    stale_triggered_at = datetime.now(UTC) - timedelta(
        hours=settings.signal_triggered_ttl_hours + 1
    )
    with session_factory() as session:
        asset = _seed_signal(session, status=SignalStatus.TRIGGERED)
        signal = session.query(Signal).filter(Signal.asset_id == asset.id).one()
        signal.triggered_at = stale_triggered_at
        session.commit()
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is False


def test_has_open_signal_true_for_a_draft_inside_its_window(
    session_factory: sessionmaker[Session],
) -> None:
    """ADR-166 - otherwise every H1 close would stack another draft for the
    same move before M15 had time to confirm the first."""
    with session_factory() as session:
        asset = _seed_signal(session, status=SignalStatus.DRAFT, created_at=datetime.now(UTC))
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is True


def test_has_open_signal_false_for_a_draft_past_its_window(
    session_factory: sessionmaker[Session],
) -> None:
    """A draft M15 never confirmed is cancelled - it must stop blocking."""
    stale = datetime.now(UTC) - timedelta(hours=settings.signal_confirmation_window_hours + 1)
    with session_factory() as session:
        asset = _seed_signal(session, status=SignalStatus.DRAFT, created_at=stale)
        assert _has_open_signal(SignalRepository(session), asset.id, datetime.now(UTC)) is False


class _RecordingSignalEngine:
    """Records which path a run took; returns a WAIT result."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def generate(self, asset: Asset, timeframe: Timeframe) -> SignalGenerationResult:
        self.calls.append(("generate", None))
        return self._result(asset, timeframe)

    def analyse_only(self, asset: Asset, timeframe: Timeframe, note: str) -> SignalGenerationResult:
        self.calls.append(("analyse_only", note))
        return self._result(asset, timeframe)

    @staticmethod
    def _result(asset: Asset, timeframe: Timeframe) -> SignalGenerationResult:
        return SignalGenerationResult(analysis_id=uuid.uuid4(), symbol=asset.symbol,
                                      timeframe=timeframe, recommendation=Recommendation.WAIT,
                                      signal=None)


def _process(session: Session, asset: Asset, engine: _RecordingSignalEngine, **kw: bool) -> object:
    return _process_asset(asset, Timeframe.H1, datetime.now(UTC), SignalRepository(session),
                          engine, **kw)  # type: ignore[arg-type]


def test_an_open_trade_is_still_analysed_but_never_signalled_again(
    session_factory: sessionmaker[Session],
) -> None:
    """ADR-186 - the hourly H1 job keeps the analysis current while a trade
    is open, and the one-trade rule still stops a second signal."""
    with session_factory() as session:
        asset = _seed_signal(
            session, status=SignalStatus.TRIGGERED, created_at=datetime.now(UTC)
        )
        session.get(Signal, session.query(Signal).one().id).triggered_at = datetime.now(UTC)
        session.commit()
        engine = _RecordingSignalEngine()

        result = _process(session, asset, engine, analyse_while_open=True)

        assert result is None
        assert engine.calls == [("analyse_only", OPEN_SIGNAL_NOTE)]
        assert session.query(Signal).count() == 1  # only the open one


def test_without_the_option_an_open_trade_is_skipped_entirely(
    session_factory: sessionmaker[Session],
) -> None:
    """The tight M5 job keeps the old behaviour: no analysis at all."""
    with session_factory() as session:
        asset = _seed_signal(session, status=SignalStatus.DRAFT, created_at=datetime.now(UTC))
        engine = _RecordingSignalEngine()

        assert _process(session, asset, engine, analyse_while_open=False) is None
        assert engine.calls == []


def test_with_nothing_open_the_full_path_runs(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        asset = _seed_signal(
            session, status=SignalStatus.STOPPED_OUT, created_at=datetime.now(UTC)
        )
        engine = _RecordingSignalEngine()

        _process(session, asset, engine, analyse_while_open=True)

        assert engine.calls == [("generate", None)]


def test_register_signal_schedule_runs_just_after_the_h1_close() -> None:
    """ADR-166 - on the clock, not a free-running interval whose phase
    depended on when the worker last restarted."""
    schedule = register_signal_schedule()

    entry = schedule["generate-signals-watchlist"]
    assert entry["task"] == "signals.generate_for_watchlist"
    assert isinstance(entry["schedule"], crontab)
    assert entry["schedule"].minute == {settings.signal_generation_minute}

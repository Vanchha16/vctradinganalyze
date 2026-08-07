"""Integration tests for the TP/SL/entry-trigger monitoring Celery task
(docs/51 §10, ADR-137) - in-memory SQLite, mirrors
`test_market_data_tasks.py`'s session-factory monkeypatch pattern."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, Recommendation, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.workers import signal_monitoring_tasks

_TABLES = [Asset.__table__, AIAnalysis.__table__, Signal.__table__, PriceCandle.__table__]


@pytest.fixture
def session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    monkeypatch.setattr(signal_monitoring_tasks, "SessionLocal", factory)
    yield factory


def _seed_signal(
    session: Session,
    *,
    signal_type: SignalType = SignalType.BUY,
    entry: str = "100",
    stop_loss: str = "95",
    take_profit: str = "115",
    status: SignalStatus = SignalStatus.ACTIVE,
    created_at: datetime | None = None,
    triggered_at: datetime | None = None,
) -> tuple[Asset, Signal]:
    asset = Asset(symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX)
    session.add(asset)
    session.flush()

    analysis = AIAnalysis(
        asset_id=asset.id,
        timeframe=Timeframe.H1,
        recommendation=Recommendation.BUY if signal_type == SignalType.BUY else Recommendation.SELL,
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
        signal_type=signal_type,
        entry_price=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_reward=3.0,
        confidence=80.0,
        status=status,
    )
    session.add(signal)
    session.flush()
    if created_at is not None:
        signal.created_at = created_at
    if triggered_at is not None:
        signal.triggered_at = triggered_at
    session.commit()
    return asset, signal


# Backwards-compatible alias for the pre-ADR-137 helper name.
_seed_active_signal = _seed_signal


def _seed_m1_candle(session: Session, asset: Asset, *, high: str, low: str) -> None:
    session.add(
        PriceCandle(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            timestamp=datetime.now(UTC),
            open=high,
            high=high,
            low=low,
            close=high,
        )
    )
    session.commit()


def _patch_enqueue(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_signal_outcome_delivery", enqueued.append
    )
    return enqueued


def test_active_signal_beyond_sl_but_never_touched_entry_stays_active(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for the production defect (spec §1): an XAU-shaped
    signal whose entry sits well above the current candle range, and
    whose candle range is already beyond the stop loss, must NOT be
    evaluated for SL/TP at all - it was never entered."""
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(
            session, entry="4275.00", stop_loss="4243.62", take_profit="4337.76"
        )
        _seed_m1_candle(session, asset, high="4252.50", low="4231.37")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.ACTIVE
        assert updated.triggered_at is None
        assert updated.closed_at is None
        assert updated.profit_loss is None
    assert enqueued == []


def test_price_touching_entry_triggers_signal(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(session, entry="100", stop_loss="95", take_profit="115")
        _seed_m1_candle(session, asset, high="102", low="99")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.TRIGGERED
        assert updated.triggered_at is not None
        assert updated.closed_at is None
    assert enqueued == []


def test_triggered_signal_closes_on_take_profit_hit(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(
            session,
            entry="100",
            stop_loss="95",
            take_profit="115",
            status=SignalStatus.TRIGGERED,
            triggered_at=datetime.now(UTC),
        )
        _seed_m1_candle(session, asset, high="116", low="110")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.SUCCESSFUL
        assert updated.closed_at is not None
        assert updated.profit_loss == pytest.approx(15.0)
    assert enqueued == [signal_id]


def test_triggered_signal_closes_on_stop_loss_hit(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(
            session,
            entry="100",
            stop_loss="95",
            take_profit="115",
            status=SignalStatus.TRIGGERED,
            triggered_at=datetime.now(UTC),
        )
        _seed_m1_candle(session, asset, high="99", low="94")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.STOPPED_OUT
    assert enqueued == [signal_id]


def test_same_candle_touching_entry_and_stop_loss_triggers_then_stops_out(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """§3.3's same-candle ambiguity: a gap/spike candle that touches both
    entry and stop loss must not be left dangling as TRIGGERED - Stop
    Loss takes precedence, consistent with the existing convention."""
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(session, entry="100", stop_loss="95", take_profit="115")
        _seed_m1_candle(session, asset, high="101", low="94")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.STOPPED_OUT
        assert updated.triggered_at is not None
        assert updated.closed_at is not None
    assert enqueued == [signal_id]


def test_active_signal_skips_ttl_expired_signal(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A signal past `signal_ttl_hours` is EXPIRED at read-time (ADR-088)
    even though `status` is still stored as ACTIVE - monitoring must not
    trigger or evaluate it."""
    enqueued = _patch_enqueue(monkeypatch)

    stale_created_at = datetime.now(UTC) - timedelta(hours=48)
    with session_factory() as session:
        asset, signal = _seed_signal(session, created_at=stale_created_at)
        _seed_m1_candle(session, asset, high="102", low="99")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.ACTIVE
        assert updated.triggered_at is None
    assert enqueued == []


def test_triggered_signal_past_triggered_ttl_is_left_stored_unchanged(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A TRIGGERED signal past `signal_triggered_ttl_hours` is CLOSED at
    read-time only (ADR-137 §3.4, same treatment as EXPIRED) - the
    monitoring task must not evaluate or mutate it further, and no P&L
    is ever persisted for it."""
    enqueued = _patch_enqueue(monkeypatch)

    stale_triggered_at = datetime.now(UTC) - timedelta(
        hours=settings.signal_triggered_ttl_hours + 1
    )
    with session_factory() as session:
        asset, signal = _seed_signal(
            session,
            status=SignalStatus.TRIGGERED,
            triggered_at=stale_triggered_at,
        )
        _seed_m1_candle(session, asset, high="116", low="110")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.TRIGGERED
        assert updated.closed_at is None
        assert updated.profit_loss is None
    assert enqueued == []


def test_monitor_signals_skips_asset_with_no_candles(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        _seed_signal(session)

    signal_monitoring_tasks.monitor_active_signals_task()

    assert enqueued == []


def test_sell_signal_price_touching_entry_triggers_signal(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(
            session, signal_type=SignalType.SELL, entry="100", stop_loss="105", take_profit="85"
        )
        _seed_m1_candle(session, asset, high="101", low="99")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.TRIGGERED
        assert updated.triggered_at is not None
    assert enqueued == []


def test_sell_signal_triggered_closes_on_take_profit_hit(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(
            session,
            signal_type=SignalType.SELL,
            entry="100",
            stop_loss="105",
            take_profit="85",
            status=SignalStatus.TRIGGERED,
            triggered_at=datetime.now(UTC),
        )
        _seed_m1_candle(session, asset, high="90", low="84")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.SUCCESSFUL
        assert updated.profit_loss == pytest.approx(15.0)
    assert enqueued == [signal_id]


def test_sell_signal_triggered_closes_on_stop_loss_hit(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued = _patch_enqueue(monkeypatch)

    with session_factory() as session:
        asset, signal = _seed_signal(
            session,
            signal_type=SignalType.SELL,
            entry="100",
            stop_loss="105",
            take_profit="85",
            status=SignalStatus.TRIGGERED,
            triggered_at=datetime.now(UTC),
        )
        _seed_m1_candle(session, asset, high="106", low="101")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.STOPPED_OUT
        assert updated.profit_loss == pytest.approx(-5.0)
    assert enqueued == [signal_id]


def test_register_signal_monitoring_schedule() -> None:
    schedule = signal_monitoring_tasks.register_signal_monitoring_schedule()

    assert schedule["signals-monitor-active"]["task"] == "signals.monitor_active"
    assert schedule["signals-monitor-active"]["schedule"] == 60.0

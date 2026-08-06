"""Integration tests for the TP/SL monitoring Celery task (docs/51 §10) -
in-memory SQLite, mirrors `test_market_data_tasks.py`'s session-factory
monkeypatch pattern."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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


def _seed_active_signal(
    session: Session,
    *,
    signal_type: SignalType = SignalType.BUY,
    entry: str = "100",
    stop_loss: str = "95",
    take_profit: str = "115",
    created_at: datetime | None = None,
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
        status=SignalStatus.ACTIVE,
    )
    session.add(signal)
    session.flush()
    if created_at is not None:
        signal.created_at = created_at
    session.commit()
    return asset, signal


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


def test_monitor_active_signals_closes_signal_on_take_profit_hit(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_signal_outcome_delivery", enqueued.append
    )

    with session_factory() as session:
        asset, signal = _seed_active_signal(session)
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


def test_monitor_active_signals_closes_signal_on_stop_loss_hit(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_signal_outcome_delivery", enqueued.append
    )

    with session_factory() as session:
        asset, signal = _seed_active_signal(session)
        _seed_m1_candle(session, asset, high="99", low="94")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.STOPPED_OUT
    assert enqueued == [signal_id]


def test_monitor_active_signals_leaves_signal_active_when_no_hit(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_signal_outcome_delivery", enqueued.append
    )

    with session_factory() as session:
        asset, signal = _seed_active_signal(session)
        _seed_m1_candle(session, asset, high="105", low="98")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.ACTIVE
        assert updated.closed_at is None
    assert enqueued == []


def test_monitor_active_signals_skips_ttl_expired_signal(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A signal past `signal_ttl_hours` is EXPIRED at read-time (ADR-088)
    even though `status` is still stored as ACTIVE - monitoring must not
    evaluate it for TP/SL."""
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_signal_outcome_delivery", enqueued.append
    )

    stale_created_at = datetime.now(UTC) - timedelta(hours=48)
    with session_factory() as session:
        asset, signal = _seed_active_signal(session, created_at=stale_created_at)
        _seed_m1_candle(session, asset, high="116", low="110")
        signal_id = str(signal.id)

    signal_monitoring_tasks.monitor_active_signals_task()

    with session_factory() as session:
        updated = session.get(Signal, uuid.UUID(signal_id))
        assert updated is not None
        assert updated.status == SignalStatus.ACTIVE
    assert enqueued == []


def test_monitor_active_signals_skips_asset_with_no_candles(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_signal_outcome_delivery", enqueued.append
    )

    with session_factory() as session:
        _seed_active_signal(session)

    signal_monitoring_tasks.monitor_active_signals_task()

    assert enqueued == []


def test_register_signal_monitoring_schedule() -> None:
    schedule = signal_monitoring_tasks.register_signal_monitoring_schedule()

    assert schedule["signals-monitor-active"]["task"] == "signals.monitor_active"
    assert schedule["signals-monitor-active"]["schedule"] == 60.0

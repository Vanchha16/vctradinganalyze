"""ADR-185 - smc-ict-crt-v2 design-A service and task.

State machine, D9 finality, restart/retry idempotency, the one slot shared
with v1 (C13), the daily cap (C14), stale decisions, the 3 h expiry, outcome
sync, isolation from v1's `smc_setups`, the PostgreSQL run lock, and the
task's default-off / v1-exclusive gating.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import MarketType, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup
from app.models.smc_v2_setup import SmcV2Setup, SmcV2State
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_v2_setup_repository import (
    RUN_LOCK_KEY,
    SmcV2SetupRepository,
    acquire_run_lock,
)
from app.services.smc_crt_v2 import rules
from app.services.smc_crt_v2.service import STRATEGY_NAME, SmcCrtV2Service
from tests import smc_v2_scenario as sc

M5 = timedelta(minutes=5)
DECISION_RUN = sc.MSS_T + M5 + timedelta(minutes=4)  # the first run after the shift is final

_TABLES = [
    User.__table__, Asset.__table__, AIAnalysis.__table__, Signal.__table__,
    PriceCandle.__table__, SmcSetup.__table__, SmcV2Setup.__table__, EaToken.__table__,
    EaExecutionEvent.__table__, AuditLog.__table__,
]


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    with factory() as s:
        yield s


def _asset(session) -> Asset:
    asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL, is_active=True)
    session.add(asset)
    session.flush()
    return asset


def _store(session, asset, until: datetime, *, lag: timedelta = timedelta(minutes=3)) -> None:
    """The scenario's M5 candles up to `until`, each fetched `lag` after its close."""
    have = {r for (r,) in session.execute(select(PriceCandle.timestamp)).all()}
    for c in sc.history(until):
        if c.t in have or c.t.replace(tzinfo=None) in have:
            continue
        session.add(PriceCandle(
            asset_id=asset.id, timeframe=Timeframe.M5, timestamp=c.t,
            open=Decimal(str(c.open)), high=Decimal(str(c.high)), low=Decimal(str(c.low)),
            close=Decimal(str(c.close)), volume=Decimal("1"), fetched_at=c.t + M5 + lag,
        ))
    session.flush()


def _service(session) -> SmcCrtV2Service:
    return SmcCrtV2Service(
        SmcV2SetupRepository(session), PriceCandleRepository(session), SignalRepository(session),
        AIAnalysisRepository(session), AuditLogRepository(session),
    )


def _v2_signals(session) -> list[Signal]:
    return list(session.execute(select(Signal).where(Signal.strategy == STRATEGY_NAME)).scalars())


def _row(session) -> SmcV2Setup:
    [row] = session.execute(
        select(SmcV2Setup).where(SmcV2Setup.raid_t == sc.RAID_T)).scalars().all()
    return row


def _published(session) -> tuple[object, SmcV2Setup, Signal]:
    asset = _asset(session)
    _store(session, asset, sc.MSS_T + M5)
    service = _service(session)
    service.run(asset, DECISION_RUN)
    [signal] = _v2_signals(session)
    return asset, _row(session), signal


# --- waiting -> decided -> published ----------------------------------------------
def test_waits_for_the_shift_then_publishes_one_active_signal(session):
    asset = _asset(session)
    _store(session, asset, sc.MSS_T)
    service = _service(session)
    service.run(asset, sc.MSS_T + timedelta(minutes=4))
    row = _row(session)
    assert row.state == SmcV2State.WAITING_FOR_MSS and _v2_signals(session) == []

    _store(session, asset, sc.MSS_T + M5)
    service.run(asset, DECISION_RUN)
    [signal] = _v2_signals(session)
    row = _row(session)
    assert row.state == SmcV2State.SIGNAL_CREATED and row.signal_id == signal.id
    assert signal.status is SignalStatus.ACTIVE and signal.signal_type is SignalType.BUY
    assert (signal.entry_price, signal.take_profit) == (Decimal("2002.0"), Decimal("2030.0"))
    assert signal.confidence == 0.0 and signal.strategy == "smc_ict_crt_v2_a"
    assert row.decided_at.replace(tzinfo=UTC) == sc.MSS_T + M5
    assert row.published_at.replace(tzinfo=UTC) == DECISION_RUN
    assert row.trading_day == rules.trading_day(DECISION_RUN)
    assert row.modelled_spread == Decimal("0.26") and 0 < row.modelled_cost_r <= 0.10
    analysis = session.get(AIAnalysis, signal.analysis_id)
    assert analysis.prompt_version == "smc-ict-crt-v2-a" and analysis.ai_available is False
    assert analysis.confidence_level == "deterministic"
    assert any("MODELLED COST" in w for w in analysis.warnings)
    assert service.created_signals == [signal.id]


def test_a_candle_that_is_not_final_yet_is_not_used(session):
    """Audit D9: the shift candle fetched too soon after its close."""
    asset = _asset(session)
    _store(session, asset, sc.MSS_T)
    _store(session, asset, sc.MSS_T + M5, lag=timedelta(seconds=30))
    _service(session).run(asset, DECISION_RUN)
    assert _row(session).state == SmcV2State.WAITING_FOR_MSS and _v2_signals(session) == []


def test_reruns_and_a_restarted_worker_never_duplicate(session):
    asset, row, signal = _published(session)
    for _ in range(3):
        _service(session).run(asset, DECISION_RUN + timedelta(minutes=1))
    assert _v2_signals(session) == [signal]
    count = session.execute(select(func.count()).select_from(SmcV2Setup)).scalar_one()
    assert count == session.execute(
        select(func.count(func.distinct(SmcV2Setup.anchor_t))).select_from(SmcV2Setup)).scalar_one()


def test_a_stale_decision_is_recorded_never_published(session):
    asset = _asset(session)
    _store(session, asset, sc.MSS_T + M5)
    _service(session).run(asset, sc.MSS_T + M5 + timedelta(minutes=25))
    row = _row(session)
    assert row.state == SmcV2State.NOT_PUBLISHED and row.reason.startswith("STALE_DECISION")
    assert _v2_signals(session) == []


# --- C13 one slot (shared with v1), C14 daily cap -----------------------------------
def _signal(session, asset, strategy, status, created=None) -> Signal:
    analysis = AIAnalysis(asset_id=asset.id, timeframe=Timeframe.M5, recommendation="BUY",
                          confidence_score=0.0, confidence_level="deterministic",
                          reasoning={}, supporting_evidence=[], conflicting_evidence=[], risks=[],
                          invalidation_conditions=[], model_name="none", prompt_version="x",
                          ai_available=False, warnings=[])
    session.add(analysis)
    session.flush()
    signal = Signal(analysis_id=analysis.id, asset_id=asset.id, timeframe=Timeframe.M5,
                    signal_type=SignalType.BUY, entry_price=Decimal("1"), stop_loss=Decimal("0.5"),
                    take_profit=Decimal("2"), risk_reward=2.0, confidence=0.0, strategy=strategy,
                    status=status)
    session.add(signal)
    session.flush()
    if created is not None:
        signal.created_at = created
    return signal


def test_an_open_v1_signal_holds_the_slot(session):
    asset = _asset(session)
    v1 = _signal(session, asset, "smc_ict_crt_v1", SignalStatus.TRIGGERED)
    _store(session, asset, sc.MSS_T + M5)
    _service(session).run(asset, DECISION_RUN)
    row = _row(session)
    assert row.state == SmcV2State.NOT_PUBLISHED and row.reason.startswith("REJECT_OPEN_TRADE")
    assert row.slot_signal_id == v1.id and _v2_signals(session) == []


def test_a_pending_v2_order_holds_the_slot_but_a_closed_one_does_not(session):
    asset = _asset(session)
    _signal(session, asset, STRATEGY_NAME, SignalStatus.STOPPED_OUT)
    _signal(session, asset, "bbma", SignalStatus.ACTIVE)  # other strategies are not this slot
    _store(session, asset, sc.MSS_T + M5)
    _service(session).run(asset, DECISION_RUN)
    assert _row(session).state == SmcV2State.SIGNAL_CREATED


def test_the_daily_cap_of_three(session):
    asset = _asset(session)
    day = rules.trading_day(DECISION_RUN)
    for i in range(rules.DAILY_CAP):
        closed = _signal(session, asset, STRATEGY_NAME, SignalStatus.STOPPED_OUT)
        session.add(SmcV2Setup(
            asset_id=asset.id, strategy=STRATEGY_NAME, design="A", anchor_timeframe="H1",
            anchor_t=sc.START + timedelta(hours=i), raid_t=sc.START + timedelta(hours=i + 1),
            state=str(SmcV2State.TRADED), direction="buy", crt_high=Decimal("1"),
            crt_low=Decimal("0"), raid_extreme=Decimal("0"), closed_back_inside=True,
            modelled_spread=Decimal("0.26"), news_status="NEWS_UNKNOWN", transitions=[],
            signal_id=closed.id, trading_day=day,
        ))
    session.flush()
    _store(session, asset, sc.MSS_T + M5)
    _service(session).run(asset, DECISION_RUN)
    row = _row(session)
    assert row.state == SmcV2State.NOT_PUBLISHED and row.reason.startswith("REJECT_DAILY_CAP")
    assert row.published_today == rules.DAILY_CAP and row.signal_id is None
    assert all(sig.status is SignalStatus.STOPPED_OUT for sig in _v2_signals(session))


# --- expiry and outcomes -------------------------------------------------------------
def test_an_unfilled_signal_is_cancelled_at_the_three_hour_expiry(session):
    asset, row, signal = _published(session)
    _service(session).run(asset, sc.EXPIRES_AT - timedelta(minutes=1))
    assert signal.status is SignalStatus.ACTIVE
    _service(session).run(asset, sc.EXPIRES_AT + timedelta(minutes=1))
    assert signal.status is SignalStatus.CANCELLED
    assert signal.status_reason == "smc-ict-crt-v2-a: 3h setup expiry, never filled"
    assert _row(session).state == SmcV2State.EXPIRED


def test_a_closed_trade_is_recorded_as_paper_when_no_live_position_existed(session):
    asset, row, signal = _published(session)
    signal.status = SignalStatus.STOPPED_OUT
    session.flush()
    _service(session).run(asset, DECISION_RUN + timedelta(minutes=30))
    row = _row(session)
    assert row.state == SmcV2State.TRADED and "paper" in row.reason


def test_v1_records_are_never_touched(session):
    _published(session)
    assert session.execute(select(func.count()).select_from(SmcSetup)).scalar_one() == 0


def test_enabling_late_does_not_backfill_old_raids(session):
    asset = _asset(session)
    _store(session, asset, sc.EXPIRES_AT + timedelta(hours=2))
    _service(session).run(asset, sc.EXPIRES_AT + timedelta(hours=2))
    rows = session.execute(select(SmcV2Setup)).scalars().all()
    assert all(r.raid_t.replace(tzinfo=UTC) >= sc.EXPIRES_AT - timedelta(hours=3) for r in rows)
    assert _v2_signals(session) == []


# --- concurrency: the run lock -------------------------------------------------------
class _Dialect:
    def __init__(self, name):
        self.name = name


class _Bind:
    def __init__(self, name):
        self.dialect = _Dialect(name)


class _RecordingSession:
    def __init__(self, dialect):
        self._bind = _Bind(dialect)
        self.executed = []

    def get_bind(self):
        return self._bind

    def execute(self, statement, params=None):
        self.executed.append((str(statement), params))


def test_the_run_lock_is_a_transaction_scoped_advisory_lock_on_postgresql():
    pg = _RecordingSession("postgresql")
    assert acquire_run_lock(pg) is True
    assert pg.executed == [("SELECT pg_advisory_xact_lock(:key)", {"key": RUN_LOCK_KEY})]
    sqlite = _RecordingSession("sqlite")
    assert acquire_run_lock(sqlite) is False and sqlite.executed == []


# --- the task --------------------------------------------------------------------------
def test_task_does_nothing_while_disabled_or_while_v1_is_on(monkeypatch):
    from app.config import settings
    from app.workers import smc_v2_tasks

    def boom():
        raise AssertionError("must not open a session")

    monkeypatch.setattr(smc_v2_tasks, "SessionLocal", boom)
    monkeypatch.setattr(settings, "smc_v2_enabled", False)
    monkeypatch.setattr(settings, "smc_enabled", False)
    smc_v2_tasks.run_smc_v2_task()  # default off: nothing
    monkeypatch.setattr(settings, "smc_v2_enabled", True)
    monkeypatch.setattr(settings, "smc_enabled", True)
    smc_v2_tasks.run_smc_v2_task()  # v1 still on: nothing


def test_switch_defaults_off_and_is_registered_for_the_admin_page():
    from app.config.settings import Settings
    from app.services.runtime_settings import REGISTRY

    assert Settings.model_fields["smc_v2_enabled"].default is False
    entry = next(s for s in REGISTRY if s.field == "smc_v2_enabled")
    assert entry.kind == "bool" and entry.group == "strategies"


def test_task_is_scheduled_after_m5_collection():
    from app.workers.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["smc-v2-run"]
    assert entry["task"] == "smc_v2.run"
    assert "smc_v2.run" in celery_app.tasks

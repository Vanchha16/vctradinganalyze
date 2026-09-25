"""ADR-183 audit fixes D1-D4 - execution plumbing around smc-ict-crt-v1.

None of these change a strategy decision: the frozen rules still produce the
same setups, entries, stops and targets (test_smc_crt_parity.py). What is
tested here is what happens *after* the strategy has decided:

D1  the signal reaches Telegram, exactly once;
D2  an order a broker cannot hold never reaches the EA;
D3  a refused signal is recorded as refused - never as a trade or a loss;
D4  a refused signal never holds the one-trade capacity.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.base import Base
from app.dependencies.ea import get_ea_service
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.broker_order import BrokerOrder
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import MarketType, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup, SmcSetupState
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.services import ea_signal_sync
from app.services.ea_signal_sync import SignalMove
from app.services.smc_crt.execution_safety import (
    EXECUTION_REJECTED_REASON,
    EXECUTION_SAFETY_REASON,
    geometry_violation,
    is_execution_rejection,
)
from app.services.smc_crt.service import STRATEGY_NAME, SmcCrtService
from app.workers import signal_monitoring_tasks, smc_tasks

H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)
M1 = timedelta(minutes=1)
T0 = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)

_TABLES = [
    User.__table__, Asset.__table__, AIAnalysis.__table__, Signal.__table__,
    PriceCandle.__table__, SmcSetup.__table__, EaToken.__table__,
    EaExecutionEvent.__table__, AuditLog.__table__, BrokerOrder.__table__,
]


@pytest.fixture
def factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


@pytest.fixture
def session(factory) -> Session:
    with factory() as s:
        yield s


# --- fixtures built from the frozen rules ----------------------------------
def _asset(session: Session) -> Asset:
    asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL, is_active=True)
    session.add(asset)
    session.flush()
    return asset


def _store(session, asset, timeframe, start, step, rows):
    for i, (o, h, low, c) in enumerate(rows):
        session.add(PriceCandle(
            asset_id=asset.id, timeframe=timeframe, timestamp=start + step * i,
            open=Decimal(str(o)), high=Decimal(str(h)), low=Decimal(str(low)),
            close=Decimal(str(c)), volume=Decimal("1"),
        ))
    session.flush()


def _service(session) -> SmcCrtService:
    return SmcCrtService(
        SmcSetupRepository(session), PriceCandleRepository(session),
        SignalRepository(session), AIAnalysisRepository(session), AuditLogRepository(session),
    )


#: A bullish CRT at a key level: earlier H4 low 88, anchor 90-130, raid to 88
#: closing back inside.
CRT_H4 = [(100, 101, 99, 100)] * 19 + [(100, 101, 88, 100), (100, 130, 90, 105),
                                        (105, 106, 88, 100)]

#: M5 that confirms the CRT (close above a confirmed swing high at 99) with
#: the entry zone ABOVE the raid low: stop below entry, a valid BUY.
VALID_M5 = [(95, 95.5, 94.5, 95)] * 14 + [
    (95, 96, 94, 95), (95, 96, 94, 95), (95, 97, 94.5, 96), (96, 98, 95, 97),
    (97, 99, 96, 98), (98, 98.5, 96, 96.5), (96.5, 97, 95.5, 96),
    (96, 101, 96, 100.5), (100.5, 102, 100, 101),
]

#: The same CRT, but M5 trades back BELOW the raid low before shifting up: the
#: frozen rules then put the FVG entry (86.6) under the stop (88 minus the
#: buffer). The known v1 geometry defect, produced by the real rules.
INVERTED_M5 = [(86, 86.5, 85.5, 86)] * 14 + [
    (86, 86.6, 85.6, 86.2), (86.2, 87, 86, 86.8), (86.8, 86.9, 86.1, 86.3),
    (86.3, 86.7, 85.9, 86.1), (86.1, 86.4, 86.0, 86.3), (86.3, 86.95, 86.3, 86.9),
    (86.9, 88.5, 86.6, 88.2),                       # closes above the 87 swing: MSS
    (88.2, 88.4, 87.9, 88.1),
]


def _load(session, m5_rows, h4_rows=CRT_H4):
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, h4_rows)
    raid_close = T0 + H4 * len(h4_rows)
    _store(session, asset, Timeframe.M5, raid_close, M5, m5_rows)
    return asset, raid_close + M5 * len(m5_rows) + M5


def _smc_signals(session) -> list[Signal]:
    return session.query(Signal).filter(Signal.strategy == STRATEGY_NAME).all()


def _feed(session) -> list:
    return get_ea_service(session).open_signals("XAUUSD", datetime.now(UTC))


# =============================================================================
# D2 - geometry: the execution-safety check itself
# =============================================================================
@pytest.mark.parametrize(
    ("signal_type", "entry", "sl", "tp", "valid"),
    [
        (SignalType.BUY, "100", "95", "110", True),     # valid BUY
        (SignalType.BUY, "100", "100", "110", False),   # invalid BUY: SL == entry
        (SignalType.BUY, "100", "101", "110", False),   # invalid BUY: SL > entry
        (SignalType.BUY, "100", "95", "100", False),    # invalid BUY: TP == entry
        (SignalType.BUY, "100", "95", "99", False),     # invalid BUY: TP < entry
        (SignalType.SELL, "100", "105", "90", True),    # valid SELL
        (SignalType.SELL, "100", "100", "90", False),   # invalid SELL: SL == entry
        (SignalType.SELL, "100", "99", "90", False),    # invalid SELL: SL < entry
        (SignalType.SELL, "100", "105", "100", False),  # invalid SELL: TP == entry
        (SignalType.SELL, "100", "105", "101", False),  # invalid SELL: TP > entry
    ],
)
def test_geometry(signal_type, entry, sl, tp, valid):
    result = geometry_violation(signal_type, Decimal(entry), Decimal(sl), Decimal(tp))
    assert (result is None) is valid


# =============================================================================
# D2 + D3 - an impossible order, end to end through the real rules
# =============================================================================
def test_the_frozen_rules_still_produce_the_inverted_setup(session):
    """The strategy decision is unchanged: the setup still passes every v1
    gate and still carries the same inverted levels."""
    asset, now = _load(session, INVERTED_M5)
    setup = _service(session).run(asset, now)[-1]
    assert setup.entry is not None and setup.stop_loss is not None
    assert setup.entry < setup.stop_loss                      # the v1 defect, untouched
    assert setup.take_profit == Decimal("130")                # CRT high
    assert setup.risk_reward >= 2.0                           # passed the v1 R:R gate


def test_invalid_geometry_is_an_execution_rejection_not_a_trade(session):
    asset, now = _load(session, INVERTED_M5)
    setup = _service(session).run(asset, now)[-1]

    assert setup.state is SmcSetupState.EXECUTION_REJECTED
    path = [t["to"] for t in setup.transitions]
    assert path[-2:] == ["signal_created", "execution_rejected"]

    [signal] = _smc_signals(session)                          # preserved for audit
    assert signal.status is SignalStatus.CANCELLED            # never ACTIVE
    assert signal.status_reason.startswith(EXECUTION_SAFETY_REASON)
    assert signal.triggered_at is None
    assert signal.profit_loss is None                         # no R, no loss
    assert signal.status not in (SignalStatus.STOPPED_OUT, SignalStatus.SUCCESSFUL)


def test_an_invalid_order_never_reaches_the_ea_or_a_broker(session):
    asset, now = _load(session, INVERTED_M5)
    _service(session).run(asset, now)
    assert _feed(session) == []                               # the EA can submit nothing
    assert session.query(BrokerOrder).count() == 0            # no server-side order either


def test_the_feed_refuses_an_invalid_order_even_if_one_were_active(session):
    """The second guard: an ACTIVE row with impossible geometry - from any
    path - is still never handed to the EA."""
    asset = _asset(session)
    analysis = AIAnalysis(asset_id=asset.id, timeframe=Timeframe.M5,
                          recommendation="BUY", confidence_score=0.0,
                          confidence_level="deterministic", model_name="none",
                          prompt_version="t", ai_available=False, reasoning={},
                          supporting_evidence=[], conflicting_evidence=[], risks=[],
                          invalidation_conditions=[], warnings=[])
    session.add(analysis)
    session.flush()
    for entry, sl in (("100", "101"), ("100", "95")):         # invalid, then valid
        session.add(Signal(analysis_id=analysis.id, asset_id=asset.id,
                           timeframe=Timeframe.M5, signal_type=SignalType.BUY,
                           entry_price=Decimal(entry), stop_loss=Decimal(sl),
                           take_profit=Decimal("110"), risk_reward=2.0, confidence=0.0,
                           strategy=STRATEGY_NAME, status=SignalStatus.ACTIVE))
    session.flush()
    feed = _feed(session)
    assert [f.signal.stop_loss for f in feed] == [Decimal("95")]


def test_an_execution_rejection_is_audited(session):
    asset, now = _load(session, INVERTED_M5)
    _service(session).run(asset, now)
    [row] = session.query(AuditLog).filter(AuditLog.action == "smc_execution_rejected").all()
    assert row.user_id is None                                # the system refused it
    assert row.context["reason"] == EXECUTION_SAFETY_REASON
    assert "not below entry" in row.context["detail"]


def test_the_m1_monitor_never_turns_a_rejection_into_a_loss(session, factory, monkeypatch):
    """The exact failure the audit found: price later touches the entry and
    the stop. The monitor only scans ACTIVE/TRIGGERED signals, so the refused
    signal stays refused - no fill, no stop-out, no R."""
    asset, now = _load(session, INVERTED_M5)
    _service(session).run(asset, now)
    session.commit()
    [signal] = _smc_signals(session)
    # M1 falls through the entry (86.6) and far below the stop.
    _store(session, asset, Timeframe.M1, now, M1, [(88, 88, 80, 81)] * 5)
    session.commit()

    monkeypatch.setattr(signal_monitoring_tasks, "SessionLocal", factory)
    for name in ("enqueue_signal_triggered_delivery", "enqueue_signal_outcome_delivery"):
        monkeypatch.setattr(f"app.workers.telegram_tasks.{name}", lambda *_: None)
    signal_monitoring_tasks.monitor_active_signals_task()

    with factory() as check:
        after = check.get(Signal, signal.id)
        assert after.status is SignalStatus.CANCELLED
        assert after.triggered_at is None and after.profit_loss is None


# =============================================================================
# D3 - a live EA/broker refusal of a valid SMC signal
# =============================================================================
def _event(signal: Signal, event_type: str, *, dry_run: bool = False) -> EaExecutionEvent:
    return EaExecutionEvent(
        user_id=signal.id, signal_id=signal.id, event_key=f"{event_type}:{signal.id}",
        event_type=event_type, dry_run=dry_run, occurred_at=datetime.now(UTC),
        account_login="1", broker_symbol="XAUUSDc", retcode=10016, message="Invalid stops",
    )


def test_a_live_ea_rejection_cancels_the_smc_signal_with_an_unambiguous_reason(session):
    asset, now = _load(session, VALID_M5)
    _service(session).run(asset, now)
    [signal] = _smc_signals(session)
    assert signal.status is SignalStatus.ACTIVE

    change = ea_signal_sync.apply_event(signal, _event(signal, "order_rejected"))
    assert change is not None and change.move is SignalMove.EXECUTION_REJECTED
    assert change.has_message is False            # never a subscriber "outcome" message
    assert signal.status is SignalStatus.CANCELLED
    assert signal.status_reason.startswith(EXECUTION_REJECTED_REASON)
    assert is_execution_rejection(signal.status_reason)
    assert signal.profit_loss is None

    # The next run records the setup as refused, not traded.
    session.flush()  # this test session has autoflush off
    setup = session.query(SmcSetup).filter(SmcSetup.signal_id == signal.id).one()
    _service(session).run(asset, now + M5)
    assert setup.state is SmcSetupState.EXECUTION_REJECTED


@pytest.mark.parametrize("event_type", ["order_rejected", "order_skipped"])
def test_ea_refusals_are_scoped_to_smc_and_to_live_events(session, event_type):
    asset, now = _load(session, VALID_M5)
    _service(session).run(asset, now)
    [signal] = _smc_signals(session)

    assert ea_signal_sync.apply_event(signal, _event(signal, event_type, dry_run=True)) is None
    assert signal.status is SignalStatus.ACTIVE   # a dry-run check is not an execution

    signal.strategy = "bbma"                      # another strategy's handling is unchanged
    assert ea_signal_sync.apply_event(signal, _event(signal, event_type)) is None
    assert signal.status is SignalStatus.ACTIVE


# =============================================================================
# D4 - a refused signal never holds the one-trade capacity
# =============================================================================
def test_an_execution_rejection_does_not_block_the_next_valid_setup(session):
    """Two CRTs eight hours apart - inside the first one's 12 h window. The
    first is refused at execution; the second must still become a signal."""
    h4 = CRT_H4 + [(100, 130, 90, 105), (105, 106, 88, 100)]
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, h4)
    _store(session, asset, Timeframe.M5, T0 + H4 * 22, M5, INVERTED_M5)
    _store(session, asset, Timeframe.M5, T0 + H4 * 24, M5, VALID_M5)

    setups = _service(session).run(asset, T0 + H4 * 24 + M5 * (len(VALID_M5) + 1))
    states = [s.state for s in setups if s.state in (
        SmcSetupState.EXECUTION_REJECTED, SmcSetupState.SIGNAL_CREATED, SmcSetupState.CANCELLED)]
    assert SmcSetupState.EXECUTION_REJECTED in states
    assert SmcSetupState.SIGNAL_CREATED in states, "the refusal must not block a valid setup"
    assert not [s for s in setups if s.reason == "REJECT_OPEN_TRADE"]


@pytest.mark.parametrize(
    ("status", "reason", "holds_capacity"),
    [
        (SignalStatus.ACTIVE, None, True),                     # pending broker order
        (SignalStatus.TRIGGERED, None, True),                  # open position
        (SignalStatus.CANCELLED, f"{EXECUTION_SAFETY_REASON}: x", False),
        (SignalStatus.CANCELLED, f"{EXECUTION_REJECTED_REASON}: x", False),
        (SignalStatus.STOPPED_OUT, None, False),               # closed trade
        (SignalStatus.SUCCESSFUL, None, False),
        (SignalStatus.CLOSED, None, False),
    ],
)
def test_one_trade_accounting(session, status, reason, holds_capacity):
    asset, now = _load(session, VALID_M5)
    _service(session).run(asset, now)
    [signal] = _smc_signals(session)
    signal.status, signal.status_reason = status, reason
    session.flush()
    count = SmcSetupRepository(session).open_signal_count(asset.id, STRATEGY_NAME)
    assert (count == 1) is holds_capacity


# =============================================================================
# D1 - Telegram delivery, exactly once, after the commit
# =============================================================================
class _FixedClock(datetime):
    moment: datetime = T0

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return cls.moment


@pytest.fixture
def task_env(factory, monkeypatch):
    """Run the real Celery task body against the test database at a fixed
    time, recording deliveries instead of sending them."""
    delivered: list[str] = []
    notices: list[str] = []
    monkeypatch.setattr(smc_tasks, "SessionLocal", factory)
    monkeypatch.setattr(settings, "smc_enabled", True)
    monkeypatch.setattr("app.workers.telegram_tasks.enqueue_signal_delivery", delivered.append)
    monkeypatch.setattr(smc_tasks.notify_execution_rejected_task, "delay", notices.append)
    monkeypatch.setattr(smc_tasks, "datetime", _FixedClock)
    return delivered, notices


def _seed(factory, m5_rows):
    with factory() as s:
        _, now = _load(s, m5_rows)
        s.commit()
    _FixedClock.moment = now


def test_a_created_signal_is_enqueued_for_telegram_exactly_once(factory, task_env):
    delivered, notices = task_env
    _seed(factory, VALID_M5)
    smc_tasks.run_smc_task()
    with factory() as s:
        [signal] = _smc_signals(s)
        assert signal.status is SignalStatus.ACTIVE       # still ACTIVE at once, no DRAFT
    assert delivered == [str(signal.id)]
    assert notices == []


def test_a_retried_run_does_not_deliver_twice(factory, task_env):
    delivered, _ = task_env
    _seed(factory, VALID_M5)
    smc_tasks.run_smc_task()
    smc_tasks.run_smc_task()                              # a retry, or simply the next tick
    _FixedClock.moment += M5
    smc_tasks.run_smc_task()
    assert len(delivered) == 1
    with factory() as s:
        assert len(_smc_signals(s)) == 1


def test_a_telegram_failure_creates_no_duplicate_signal(factory, task_env, monkeypatch):
    def broken(_signal_id):
        raise ConnectionError("broker down")

    monkeypatch.setattr("app.workers.telegram_tasks.enqueue_signal_delivery", broken)
    _seed(factory, VALID_M5)
    smc_tasks.run_smc_task()                              # must not raise
    smc_tasks.run_smc_task()
    with factory() as s:
        assert len(_smc_signals(s)) == 1


def test_the_ea_handoff_does_not_depend_on_telegram(factory, task_env, monkeypatch):
    def broken(_signal_id):
        raise ConnectionError("telegram down")

    monkeypatch.setattr("app.workers.telegram_tasks.enqueue_signal_delivery", broken)
    _seed(factory, VALID_M5)
    smc_tasks.run_smc_task()
    with factory() as s:
        feed = _feed(s)
        assert len(feed) == 1 and feed[0].signal.strategy == STRATEGY_NAME


def test_a_rejected_signal_sends_a_rejection_notice_not_a_signal(factory, task_env):
    delivered, notices = task_env
    _seed(factory, INVERTED_M5)
    smc_tasks.run_smc_task()
    assert delivered == []                                # never broadcast as a trade call
    with factory() as s:
        [signal] = _smc_signals(s)
        assert notices == [str(signal.id)]
        text = smc_tasks.compose_execution_rejected_message(signal)
    assert "REJECTED BY EXECUTION SAFETY" in text
    assert "not a trade and not a loss" in text

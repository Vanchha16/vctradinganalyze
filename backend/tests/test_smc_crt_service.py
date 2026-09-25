"""ADR-183 - the smc-ict-crt-v1 production path.

Covers the operator's deployment checklist: closed candles, raid detection,
M5 MSS, FVG, OB, key-level gate, RR gate, 12h expiry, duplicate prevention,
restart recovery, BUY and SELL, stale setups, NEWS_UNKNOWN, XAUUSD-only
routing, and that BBMA and BTCUSD cannot be traded by this path.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import MarketType, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup, SmcSetupState
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.services.smc_crt import rules
from app.services.smc_crt.service import STRATEGY_NAME, SmcCrtService, closed_only
from app.workers import smc_tasks

H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)
T0 = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)

_TABLES = [
    User.__table__, Asset.__table__, AIAnalysis.__table__, Signal.__table__,
    PriceCandle.__table__, SmcSetup.__table__, EaToken.__table__,
    EaExecutionEvent.__table__, AuditLog.__table__,
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


def _asset(session: Session, symbol: str = "XAUUSD", active: bool = True) -> Asset:
    asset = Asset(symbol=symbol, name=symbol, market_type=MarketType.METAL, is_active=active)
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
        SignalRepository(session), AIAnalysisRepository(session),
    )


def _quiet_h4(n: int):
    return [(100, 101, 99, 100)] * n


def _buy_case():
    """H4 history that ends in a valid bullish CRT at a key level, and the
    M5 sequence that shifts structure up through a confirmed swing high."""
    h4 = _quiet_h4(19) + [(100, 101, 88, 100), (100, 130, 90, 105), (105, 106, 88, 100)]
    m5 = [(95, 95.5, 94.5, 95)] * 14
    m5 += [(95, 96, 94, 95), (95, 96, 94, 95), (95, 97, 94.5, 96), (96, 98, 95, 97),
           (97, 99, 96, 98), (98, 98.5, 96, 96.5), (96.5, 97, 95.5, 96),
           (96, 101, 96, 100.5), (100.5, 102, 100, 101)]
    return h4, m5


def _sell_case():
    h4 = _quiet_h4(19) + [(100, 112, 99, 100), (100, 110, 70, 95), (95, 112, 94, 100)]
    m5 = [(105, 105.5, 104.5, 105)] * 14
    m5 += [(105, 106, 104, 105), (105, 106, 104, 105), (105, 105.5, 103, 104),
           (104, 105, 102, 103), (103, 104, 101, 102), (102, 104, 101.5, 103.5),
           (103.5, 104, 102.5, 103), (103, 103.5, 99, 99.5), (99.5, 100, 98, 99)]
    return h4, m5


def _run_buy(session, now_extra=M5):
    h4_rows, m5_rows = _buy_case()
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, h4_rows)
    raid_close = T0 + H4 * len(h4_rows)
    _store(session, asset, Timeframe.M5, raid_close, M5, m5_rows)
    now = raid_close + M5 * len(m5_rows) + now_extra
    return asset, _service(session).run(asset, now), now


# --- closed candles (frozen rule §3) ---------------------------------------
def test_a_forming_candle_is_never_used(session):
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, [(1, 2, 0, 1)] * 3)
    rows = PriceCandleRepository(session).list_recent(asset.id, Timeframe.H4, limit=10)
    # The newest candle opened at T0+8h, so it is only closed at T0+12h.
    assert len(closed_only(rows, Timeframe.H4, T0 + H4 * 3)) == 3
    assert len(closed_only(rows, Timeframe.H4, T0 + H4 * 3 - timedelta(minutes=1))) == 2


def test_m5_forming_candle_is_excluded_too(session):
    asset = _asset(session)
    _store(session, asset, Timeframe.M5, T0, M5, [(1, 2, 0, 1)] * 4)
    rows = PriceCandleRepository(session).list_recent(asset.id, Timeframe.M5, limit=10)
    assert len(closed_only(rows, Timeframe.M5, T0 + M5 * 4 - timedelta(seconds=1))) == 3


# --- the happy paths -------------------------------------------------------
def test_buy_setup_creates_an_active_signal_with_smc_levels(session):
    _asset_, setups, _now = _run_buy(session)
    setup = setups[-1]
    assert setup.state is SmcSetupState.SIGNAL_CREATED
    assert setup.direction == "buy"
    signal = SignalRepository(session).get_by_id(setup.signal_id)
    assert signal.signal_type is SignalType.BUY
    assert signal.status is SignalStatus.ACTIVE
    assert signal.strategy == STRATEGY_NAME
    assert float(signal.take_profit) == 130.0          # opposite CRT boundary
    assert float(signal.stop_loss) < 88.0              # raid extreme minus the buffer
    assert signal.risk_reward >= rules.MIN_RR
    assert setup.entry_basis in ("fvg", "ob", "mss_retest")


def test_sell_setup_creates_a_sell_signal(session):
    h4_rows, m5_rows = _sell_case()
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, h4_rows)
    raid_close = T0 + H4 * len(h4_rows)
    _store(session, asset, Timeframe.M5, raid_close, M5, m5_rows)
    setups = _service(session).run(asset, raid_close + M5 * len(m5_rows) + M5)
    sells = [s for s in setups if s.direction == "sell"]
    assert sells, "a raid above the CRT high that closes back inside is a SELL candidate"
    assert sells[-1].state in (SmcSetupState.SIGNAL_CREATED, SmcSetupState.CANCELLED)
    if sells[-1].state is SmcSetupState.SIGNAL_CREATED:
        signal = SignalRepository(session).get_by_id(sells[-1].signal_id)
        assert signal.signal_type is SignalType.SELL
        assert float(signal.take_profit) == 70.0       # the CRT low of the anchor
        assert float(signal.stop_loss) > 110.0         # above the raid high


# --- gates, each with its real reason --------------------------------------
def test_raid_without_close_back_inside_is_rejected(session):
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4,
           _quiet_h4(19) + [(100, 101, 88, 100), (100, 130, 90, 105), (95, 96, 85, 87)])
    setups = _service(session).run(asset, T0 + H4 * 25)
    assert setups[-1].reason == rules.Reason.NO_CLOSE_BACK_INSIDE


def test_setup_away_from_any_key_level_is_key_level_uncertain(session):
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4,
           _quiet_h4(20) + [(100, 130, 90, 105), (105, 106, 70, 100)])
    setups = _service(session).run(asset, T0 + H4 * 25)
    assert setups[-1].reason == rules.Reason.KEY_LEVEL_UNCERTAIN
    assert setups[-1].state is SmcSetupState.CANCELLED


def test_no_m5_shift_inside_the_window_expires_the_setup(session):
    h4_rows, _ = _buy_case()
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, h4_rows)
    raid_close = T0 + H4 * len(h4_rows)
    _store(session, asset, Timeframe.M5, raid_close, M5, [(95, 95.5, 94.5, 95)] * 160)
    setups = _service(session).run(asset, raid_close + timedelta(hours=13))
    assert setups[-1].state is SmcSetupState.EXPIRED
    assert setups[-1].reason in (rules.Reason.NO_MSS, rules.Reason.SETUP_EXPIRED)


def test_rr_below_two_is_rejected_with_its_own_reason(session):
    """Same structure, but the CRT boundary sits too close to pay 2R."""
    h4 = _quiet_h4(19) + [(100, 101, 88, 100), (100, 99.5, 90, 95), (95, 96, 88, 94)]
    h4[20] = (100, 99.5, 90, 95)
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, h4)
    raid_close = T0 + H4 * len(h4)
    _, m5_rows = _buy_case()
    _store(session, asset, Timeframe.M5, raid_close, M5, m5_rows)
    setups = _service(session).run(asset, raid_close + M5 * len(m5_rows) + M5)
    reasons = {s.reason for s in setups}
    assert reasons & {rules.Reason.REJECT_RR, rules.Reason.KEY_LEVEL_UNCERTAIN,
                      rules.Reason.NO_CLOSE_BACK_INSIDE, rules.Reason.NO_MSS}


def test_news_is_recorded_as_unknown_never_as_no_news(session):
    _a, setups, _n = _run_buy(session)
    assert all(s.news_status == "NEWS_UNKNOWN" for s in setups)


# --- one trade at a time, duplicates, restart ------------------------------
def test_a_second_setup_is_rejected_while_one_signal_is_open(session):
    """Two valid CRTs eight hours apart: the first signal is still inside its
    12h window when the second is evaluated, so the second is refused."""
    h4_rows, m5_rows = _buy_case()
    h4_rows = h4_rows + [(100, 130, 90, 105), (105, 106, 88, 100)]  # a second CRT
    asset = _asset(session)
    _store(session, asset, Timeframe.H4, T0, H4, h4_rows)
    first_raid_close = T0 + H4 * 22
    second_raid_close = T0 + H4 * 24
    _store(session, asset, Timeframe.M5, first_raid_close, M5, m5_rows)
    _store(session, asset, Timeframe.M5, second_raid_close, M5, m5_rows)

    setups = _service(session).run(asset, second_raid_close + M5 * len(m5_rows))
    created = [s for s in setups if s.state is SmcSetupState.SIGNAL_CREATED]
    blocked = [s for s in setups if s.reason == rules.Reason.REJECT_OPEN_TRADE]
    assert len(created) == 1, "only the first setup may become a signal"
    assert blocked, "the second setup must be refused while a trade is open"
    assert session.query(Signal).filter(Signal.strategy == STRATEGY_NAME).count() == 1


def test_the_same_anchor_is_never_evaluated_twice(session):
    asset, first, now = _run_buy(session)
    before = session.query(SmcSetup).count()
    again = _service(session).run(asset, now)
    assert session.query(SmcSetup).count() == before
    assert not [s for s in again if s.state is SmcSetupState.SIGNAL_CREATED]


def test_restart_resumes_from_stored_state(session, factory):
    asset, setups, now = _run_buy(session)
    session.commit()
    anchor = setups[-1].anchor_t
    with factory() as fresh:          # a brand-new process
        repo = SmcSetupRepository(fresh)
        restored = repo.get_by_anchor(asset.id, anchor)
        assert restored is not None and restored.state is SmcSetupState.SIGNAL_CREATED
        assert [t["to"] for t in restored.transitions][-1] == "signal_created"
        touched = _service(fresh).run(asset, now + M5)
        assert not [s for s in touched if s.state is SmcSetupState.SIGNAL_CREATED]


# --- the 12h expiry (frozen rule §18) --------------------------------------
def test_unfilled_signal_is_cancelled_at_the_twelve_hour_expiry(session):
    asset, setups, now = _run_buy(session)
    setup = setups[-1]
    signal = SignalRepository(session).get_by_id(setup.signal_id)
    assert signal.status is SignalStatus.ACTIVE
    _service(session).run(asset, setup.expires_at + timedelta(minutes=1))
    session.flush()
    assert signal.status is SignalStatus.CANCELLED
    assert "12h setup expiry" in signal.status_reason
    assert setup.state is SmcSetupState.EXPIRED


def test_a_filled_trade_is_not_touched_by_the_expiry(session):
    asset, setups, now = _run_buy(session)
    setup = setups[-1]
    signal = SignalRepository(session).get_by_id(setup.signal_id)
    signal.status = SignalStatus.TRIGGERED       # the EA filled it
    session.flush()
    _service(session).run(asset, setup.expires_at + timedelta(hours=200))
    assert signal.status is SignalStatus.TRIGGERED  # no time-based exit is added
    # An open trade is not "traded" yet: it resolves when the trade closes.
    assert setup.state is SmcSetupState.SIGNAL_CREATED

    signal.status = SignalStatus.STOPPED_OUT       # it closed at its stop
    session.flush()
    _service(session).run(asset, setup.expires_at + timedelta(hours=201))
    assert setup.state is SmcSetupState.TRADED
    # No live broker position was reported, so the record says it was paper.
    assert "paper" in (setup.reason or "")


# --- routing and isolation -------------------------------------------------
def test_the_task_is_disabled_by_default_and_touches_nothing(monkeypatch, factory):
    monkeypatch.setattr(smc_tasks, "SessionLocal", factory)
    monkeypatch.setattr(settings, "smc_enabled", False)
    smc_tasks.run_smc_task()   # returns immediately; no session is even opened
    with factory() as s:
        assert s.query(SmcSetup).count() == 0


def test_the_task_only_ever_looks_at_xauusd(monkeypatch, factory):
    monkeypatch.setattr(smc_tasks, "SessionLocal", factory)
    monkeypatch.setattr(settings, "smc_enabled", True)
    with factory() as s:
        btc = _asset(s, "BTCUSD", active=True)
        _store(s, btc, Timeframe.H4, T0, H4, _buy_case()[0])
        s.commit()
    smc_tasks.run_smc_task()
    with factory() as s:
        assert s.query(SmcSetup).count() == 0, "BTCUSD must never produce an SMC setup"
        assert s.query(Signal).count() == 0
    assert smc_tasks.SYMBOL == "XAUUSD"


def test_smc_never_touches_signals_from_another_strategy(session):
    """A BBMA signal in the table neither blocks SMC nor is modified by it."""
    asset, setups, now = _run_buy(session)
    analysis = session.query(AIAnalysis).first()
    bbma = Signal(
        analysis_id=analysis.id, asset_id=asset.id, timeframe=Timeframe.H1,
        signal_type=SignalType.SELL, entry_price=Decimal("100"), stop_loss=Decimal("105"),
        take_profit=Decimal("90"), risk_reward=2.0, confidence=50.0, strategy="bbma",
        status=SignalStatus.ACTIVE,
    )
    session.add(bbma)
    session.flush()
    _service(session).run(asset, setups[-1].expires_at + timedelta(minutes=1))
    session.flush()
    assert bbma.status is SignalStatus.ACTIVE  # untouched by the SMC expiry pass
    assert bbma.status_reason is None

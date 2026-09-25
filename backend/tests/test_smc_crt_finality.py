"""Audit D9 - the smc-ict-crt-v1 path decides on final candles only.

The collector stores the forming candle and rewrites it in place, so a
candle whose period has ended can still hold the values it had while it was
forming. Production proved it on 2026-09-25: the H4 raid candle opened 05:00
was read at 09:00 with its 05:44 values (a clean bullish CRT) while its
final values sweep both sides of the anchor (no CRT at all), and M5 candles
read at the SMC tick moved by up to 3.37 once re-fetched.

These tests pin the finality rule (`is_final`, applied by `closed_only`)
without touching the frozen rules: a stale candle cannot create a setup, a
false shift or a level; the same candle once final gives exactly the frozen
rules' answer.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import MarketType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup, SmcSetupState
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.services.smc_crt import rules
from app.services.smc_crt.service import PUBLICATION_LAG, SmcCrtService, closed_only, is_final

H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)

_TABLES = [
    User.__table__, Asset.__table__, AIAnalysis.__table__, Signal.__table__,
    PriceCandle.__table__, SmcSetup.__table__, EaToken.__table__,
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


def _add(session, asset, timeframe, t, ohlc, fetched_at) -> PriceCandle:
    o, h, low, c = ohlc
    row = PriceCandle(
        asset_id=asset.id, timeframe=timeframe, timestamp=t,
        open=Decimal(str(o)), high=Decimal(str(h)), low=Decimal(str(low)),
        close=Decimal(str(c)), volume=Decimal("1"), fetched_at=fetched_at,
    )
    session.add(row)
    session.flush()
    return row


def _refetch(session, row: PriceCandle, ohlc, fetched_at) -> None:
    """What a later collection run does: rewrite the same row in place."""
    o, h, low, c = ohlc
    row.open, row.high, row.low, row.close = (Decimal(str(x)) for x in (o, h, low, c))
    row.fetched_at = fetched_at
    session.flush()


def _final(t, step) -> datetime:
    """A fetch comfortably after the candle's close: its values are final."""
    return t + step + PUBLICATION_LAG + timedelta(minutes=1)


def _service(session) -> SmcCrtService:
    return SmcCrtService(
        SmcSetupRepository(session), PriceCandleRepository(session),
        SignalRepository(session), AIAnalysisRepository(session),
    )


def _setups(session) -> list[SmcSetup]:
    return session.query(SmcSetup).order_by(SmcSetup.anchor_t).all()


# --- the finality rule itself ------------------------------------------------
def test_a_candle_is_final_only_when_fetched_after_its_close_plus_the_lag(session):
    asset = _asset(session)
    t = datetime(2026, 9, 25, 5, tzinfo=UTC)
    close = t + H4
    row = _add(session, asset, Timeframe.H4, t, (1, 2, 0, 1), None)
    assert not is_final(row, Timeframe.H4)                  # never fetched with a stamp
    row.fetched_at = t + timedelta(minutes=44, seconds=33)  # production's 05:44:33 write
    assert not is_final(row, Timeframe.H4)
    row.fetched_at = close + PUBLICATION_LAG - timedelta(seconds=1)
    assert not is_final(row, Timeframe.H4)
    row.fetched_at = close + PUBLICATION_LAG
    assert is_final(row, Timeframe.H4)


def test_closed_only_drops_the_newest_closed_candles_until_one_is_final(session):
    asset = _asset(session)
    t0 = datetime(2026, 9, 25, 9, tzinfo=UTC)
    rows = [
        _add(session, asset, Timeframe.M5, t0, (1, 2, 0, 1), None),  # older, pre-D9 row
        _add(session, asset, Timeframe.M5, t0 + M5, (1, 2, 0, 1), _final(t0 + M5, M5)),
        _add(session, asset, Timeframe.M5, t0 + M5 * 2, (1, 2, 0, 1), t0 + M5 * 2 + M5 * 0.8),
    ]
    now = t0 + M5 * 3 + timedelta(minutes=1)          # all three closed
    kept = closed_only(rows, Timeframe.M5, now)
    assert [c.t for c in kept] == [t0, t0 + M5]      # the unconfirmed newest one is left out


# --- H4: the exact 2026-09-25 case -------------------------------------------
_ANCHOR_0925 = (4280.22171, 4295.53265, 4262.93802, 4263.18147)       # 01:00
_RAID_0925_STALE = (4263.56582, 4274.96851, 4257.31193, 4274.85775)   # 05:00 as of 05:44:33
_RAID_0925_FINAL = (4263.56582, 4296.08627, 4257.31193, 4294.51900)   # 05:00 final


def _h4_0925(session, asset, raid_ohlc, raid_fetched_at) -> PriceCandle:
    anchor_t = datetime(2026, 9, 25, 1, tzinfo=UTC)
    start = anchor_t - H4 * 20
    for i in range(20):  # quiet history: no sweep, so no candidate of its own
        t = start + H4 * i
        _add(session, asset, Timeframe.H4, t, (4280, 4281, 4279, 4280), _final(t, H4))
    _add(session, asset, Timeframe.H4, anchor_t, _ANCHOR_0925, _final(anchor_t, H4))
    return _add(session, asset, Timeframe.H4, anchor_t + H4, raid_ohlc, raid_fetched_at)


def test_the_0925_raid_is_a_crt_on_its_stale_values_and_not_on_its_final_ones():
    """The frozen rules themselves: the production decision was built on the
    05:44 snapshot; the finished candle swept both sides of the anchor."""
    t = datetime(2026, 9, 25, 1, tzinfo=UTC)
    anchor = rules.Candle(t, *_ANCHOR_0925)
    stale = rules.Candle(t + H4, *_RAID_0925_STALE)
    final = rules.Candle(t + H4, *_RAID_0925_FINAL)

    on_stale = rules.crt_candidate([anchor, stale], 1)
    assert on_stale is not None and on_stale.direction is rules.Direction.BUY
    assert on_stale.closed_back_inside and on_stale.raid_extreme == 4257.31193
    assert rules.crt_candidate([anchor, final], 1) is None


def test_the_0925_stale_raid_creates_no_setup_until_final_and_then_none(session):
    asset = _asset(session)
    raid = _h4_0925(session, asset, _RAID_0925_STALE,
                    datetime(2026, 9, 25, 5, 44, 33, tzinfo=UTC))
    service = _service(session)
    # Every tick between the close (09:00) and the old 09:44 re-fetch read
    # the 05:44 snapshot in production. Now none of them can use it.
    for minute in (4, 9, 29, 43):
        service.run(asset, datetime(2026, 9, 25, 9, minute, tzinfo=UTC))
        assert _setups(session) == []

    _refetch(session, raid, _RAID_0925_FINAL, datetime(2026, 9, 25, 9, 44, 33, tzinfo=UTC))
    service.run(asset, datetime(2026, 9, 25, 9, 49, tzinfo=UTC))
    assert _setups(session) == []  # final candle: not a CRT, so nothing to record


def test_a_stale_h4_raid_is_never_used_however_late_the_fetch(session):
    """A missed or late fetch leaves the candle out - it is never promoted
    to final by the passing of time."""
    asset = _asset(session)
    _h4_0925(session, asset, _RAID_0925_STALE, datetime(2026, 9, 25, 5, 44, 33, tzinfo=UTC))
    for now in (
        datetime(2026, 9, 25, 10, 4, tzinfo=UTC),
        datetime(2026, 9, 25, 12, 59, tzinfo=UTC),
    ):
        _service(session).run(asset, now)
    assert _setups(session) == []


def test_a_genuine_crt_is_evaluated_once_its_raid_candle_is_final(session):
    """The same bullish raid, this time really final: the setup is recorded
    exactly as the frozen rules decide it."""
    asset = _asset(session)
    raid = _h4_0925(session, asset, _RAID_0925_STALE,
                    datetime(2026, 9, 25, 5, 44, 33, tzinfo=UTC))
    _refetch(session, raid, _RAID_0925_STALE, datetime(2026, 9, 25, 9, 3, 10, tzinfo=UTC))

    _service(session).run(asset, datetime(2026, 9, 25, 9, 4, tzinfo=UTC))
    setups = _setups(session)
    assert len(setups) == 1
    assert setups[0].direction == "buy"
    assert float(setups[0].raid_extreme) == 4257.31193
    assert setups[0].closed_back_inside is True


# --- M5: shift, gap and stop buffer on final candles only ---------------------
_H4_BUY = [(100, 101, 99, 100)] * 19 + [
    (100, 101, 88, 100),   # earlier low at 88: the key level
    (100, 130, 90, 105),   # anchor: CRT 90-130
    (105, 106, 88, 100),   # raid: swept 88, closed back inside
]
_M5_BEFORE_SHIFT = [(95, 95.5, 94.5, 95)] * 14 + [
    (95, 96, 94, 95), (95, 96, 94, 95),
    (95, 97, 94.5, 96), (96, 98, 95, 97), (97, 99, 96, 98),  # swing high 99
    (98, 98.5, 96, 96.5), (96.5, 97, 95.5, 96),
]
_T0 = datetime(2026, 1, 5, tzinfo=UTC)


def _m5_scenario(session, newest_ohlc, newest_fetched_at):
    """Final H4 raid and final M5 history; only the newest M5 bar varies."""
    asset = _asset(session)
    for i, ohlc in enumerate(_H4_BUY):
        t = _T0 + H4 * i
        _add(session, asset, Timeframe.H4, t, ohlc, _final(t, H4))
    raid_close = _T0 + H4 * len(_H4_BUY)
    for i, ohlc in enumerate(_M5_BEFORE_SHIFT):
        t = raid_close + M5 * i
        _add(session, asset, Timeframe.M5, t, ohlc, _final(t, M5))
    newest_t = raid_close + M5 * len(_M5_BEFORE_SHIFT)
    newest = _add(session, asset, Timeframe.M5, newest_t, newest_ohlc, newest_fetched_at)
    return asset, newest, newest_t


def _frozen_rules_signal(m5_newest_ohlc) -> rules.Setup:
    """The frozen rules on a complete history whose newest M5 bar is given:
    the reference production must reproduce."""
    h4 = [rules.Candle(_T0 + H4 * i, *r) for i, r in enumerate(_H4_BUY)]
    raid_close = _T0 + H4 * len(_H4_BUY)
    rows = [*_M5_BEFORE_SHIFT, m5_newest_ohlc]
    m5 = [rules.Candle(raid_close + M5 * i, *r) for i, r in enumerate(rows)]
    setup = rules.crt_candidate(h4, len(h4) - 1)
    assert setup is not None
    found = rules.find_mss(m5, 0, len(m5) - 1, setup.direction)
    assert found is not None
    mss_index, _level = found
    setup.fvg = rules.find_fvg(m5, 0, mss_index, setup.direction)
    setup.ob = rules.find_ob(m5, mss_index, setup.direction)
    level = rules.entry_level(setup)
    assert level is not None
    setup.entry, setup.entry_basis = level
    buffer = (rules.atr(m5, mss_index, rules.ATR_PERIOD) or 0.0) * rules.SL_BUFFER_ATR_FRACTION
    pivots = [s for s in rules.swings_range(m5, 0, mss_index)
              if s.high != (setup.direction is rules.Direction.BUY)]
    rules.stops_and_targets(setup, buffer, pivots[-1].price if pivots else None)
    return setup


def test_a_stale_m5_close_cannot_create_a_false_shift(session):
    stale = (96, 100.2, 96, 100)     # as first stored: closes above the 99 swing
    final = (96, 99.5, 95.8, 98.8)   # the finished bar never closed above it
    h4 = [rules.Candle(_T0 + H4 * i, *r) for i, r in enumerate(_H4_BUY)]
    raid_close = _T0 + H4 * len(_H4_BUY)
    as_if_final = [rules.Candle(raid_close + M5 * i, *r)
                   for i, r in enumerate([*_M5_BEFORE_SHIFT, stale])]
    buy = rules.crt_candidate(h4, len(h4) - 1).direction
    assert rules.find_mss(as_if_final, 0, len(as_if_final) - 1, buy) is not None  # the trap

    t = raid_close + M5 * len(_M5_BEFORE_SHIFT)
    # Written 247 s into the bar, as production's M5 collector did.
    asset, newest, _ = _m5_scenario(session, stale, t + timedelta(minutes=4, seconds=7))
    service = _service(session)
    service.run(asset, t + M5 + timedelta(minutes=1))           # SMC tick after the close
    assert _setups(session)[-1].state is SmcSetupState.WAITING_FOR_M5_MSS
    assert session.query(Signal).count() == 0

    _refetch(session, newest, final, _final(t, M5))
    service.run(asset, t + M5 * 2 - timedelta(minutes=1))
    assert _setups(session)[-1].state is SmcSetupState.WAITING_FOR_M5_MSS
    assert session.query(Signal).count() == 0


def test_a_genuine_shift_confirms_on_final_data_with_the_frozen_levels(session):
    """Covers MSS, FVG and the ATR stop buffer: the stale snapshot of the
    shift bar would give a different gap and stop; production must wait for
    the final bar and then match the frozen rules on it exactly."""
    stale = (98.6, 100.6, 98.6, 100.5)   # same shift close, lower high and higher low
    final = (96, 101, 96, 100.5)
    frozen_final = _frozen_rules_signal(final)
    frozen_stale = _frozen_rules_signal(stale)
    assert (frozen_stale.entry, frozen_stale.sl) != (frozen_final.entry, frozen_final.sl), (
        "the fixture must make the stale bar matter, or this test proves nothing"
    )

    raid_close = _T0 + H4 * len(_H4_BUY)
    t = raid_close + M5 * len(_M5_BEFORE_SHIFT)
    asset, newest, _ = _m5_scenario(session, stale, t + timedelta(minutes=4, seconds=7))
    service = _service(session)
    service.run(asset, t + M5 + timedelta(minutes=1))
    assert session.query(Signal).count() == 0          # not on the stale snapshot

    _refetch(session, newest, final, t + M5 + timedelta(minutes=3, seconds=5))
    service.run(asset, t + M5 + timedelta(minutes=4))  # the tick after the M5 fetch
    setup = _setups(session)[-1]
    assert setup.state is SmcSetupState.SIGNAL_CREATED, setup.reason
    signal = session.get(Signal, setup.signal_id)
    assert float(signal.entry_price) == pytest.approx(frozen_final.entry)
    assert float(signal.stop_loss) == pytest.approx(frozen_final.sl)
    assert float(signal.take_profit) == pytest.approx(frozen_final.tp1)
    assert signal.risk_reward == pytest.approx(frozen_final.rr)
    assert setup.entry_basis == frozen_final.entry_basis


def test_fvg_and_atr_use_the_final_bar_not_the_snapshot():
    """The frozen functions on the two versions of the same bar: the gap and
    the ATR buffer differ, which is why only the final one may be used."""
    raid_close = _T0 + H4 * len(_H4_BUY)
    snap = [rules.Candle(raid_close + M5 * i, *r)
            for i, r in enumerate([*_M5_BEFORE_SHIFT, (98.6, 100.6, 98.6, 100.5)])]
    final = [replace(c) for c in snap[:-1]] + [
        rules.Candle(snap[-1].t, 96, 101, 96, 100.5)
    ]
    last = len(snap) - 1
    buy = rules.Direction.BUY
    assert rules.find_fvg(snap, 0, last, buy) != rules.find_fvg(final, 0, last, buy)
    assert rules.atr(snap, last, rules.ATR_PERIOD) != rules.atr(final, last, rules.ATR_PERIOD)

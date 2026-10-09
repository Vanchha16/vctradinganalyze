"""ADR-185 - smc-ict-crt-v2 design A, pure rules.

Pins: exact H1 completeness, the verified broker hours, data gaps, live
prefix decisions (waiting vs terminal, decisions stable as later candles
arrive), key levels identical to frozen v1, the broker trading day, and -
where the untracked research checkout is present - parity with the frozen
research design A on the 24-month broker history.
"""

import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from app.services.smc_crt import rules as v1rules
from app.services.smc_crt.rules import Candle, Direction, Reason
from app.services.smc_crt_v2 import rules
from app.services.smc_crt_v2.rules import Outcome
from tests import smc_v2_scenario as sc

H = timedelta(hours=1)
M5 = timedelta(minutes=5)


def _hour(t: datetime, minutes: list[int], *, second: int = 0) -> list[Candle]:
    return [Candle(t + timedelta(minutes=m, seconds=second), 1.0, 2.0, 0.5, 1.5) for m in minutes]


def _evaluate(m5: list[Candle], now: datetime):
    m5 = rules.admit(m5)
    times = [c.t for c in m5]
    series = rules.H1Series.from_buckets(rules.aggregate_h1(m5))
    index = rules.KeyLevelIndex(series)
    r = [b.t for b in series.bars].index(sc.RAID_T)
    return rules.evaluate(series, index, r, m5, times, now)


# --- H1 completeness ------------------------------------------------------
def test_an_hour_is_complete_only_with_its_twelve_on_grid_candles():
    t = datetime(2026, 10, 6, 9, tzinfo=UTC)
    full = list(range(0, 60, 5))
    [ok] = rules.aggregate_h1(_hour(t, full))
    assert ok.complete
    [missing] = rules.aggregate_h1(_hour(t, full[:-1]))
    assert not missing.complete


def test_a_duplicate_or_off_grid_stamp_does_not_count_as_complete():
    """Codex review: twelve inputs are not twelve slots."""
    t = datetime(2026, 10, 6, 9, tzinfo=UTC)
    duplicate = _hour(t, [*range(0, 55, 5), 50])  # :50 twice, :55 missing
    off_grid = _hour(t, [*range(0, 55, 5), 52])  # :52 instead of :55
    assert not rules.aggregate_h1(duplicate)[0].complete
    assert not rules.aggregate_h1(off_grid)[0].complete


def test_aggregate_keeps_first_open_extremes_and_last_close():
    t = datetime(2026, 10, 6, 9, tzinfo=UTC)
    m5 = [Candle(t + i * M5, 10.0 + i, 12.0 + i, 9.0 - i, 11.0 + i) for i in range(12)]
    [bar] = rules.aggregate_h1(m5)
    c = bar.candle
    assert (c.open, c.high, c.low, c.close) == (10.0, 23.0, -2.0, 22.0)


# --- broker hours -----------------------------------------------------------
@pytest.mark.parametrize(
    ("utc", "closed"),
    [
        (datetime(2026, 7, 7, 20, 55, tzinfo=UTC), False),  # Tue 16:55 New York (EDT)
        (datetime(2026, 7, 7, 21, 0, tzinfo=UTC), True),  # Tue 17:00 NY - daily break
        (datetime(2026, 7, 7, 22, 0, tzinfo=UTC), False),  # Tue 18:00 NY - reopened
        (datetime(2026, 1, 6, 21, 0, tzinfo=UTC), False),  # Tue 16:00 NY (EST) - open
        (datetime(2026, 1, 6, 22, 0, tzinfo=UTC), True),  # Tue 17:00 NY (EST) - break
        (datetime(2026, 7, 10, 21, 0, tzinfo=UTC), True),  # Fri 17:00 NY - weekend
        (datetime(2026, 7, 11, 12, 0, tzinfo=UTC), True),  # Saturday
        (datetime(2026, 7, 12, 21, 55, tzinfo=UTC), True),  # Sun 17:55 NY
        (datetime(2026, 7, 12, 22, 0, tzinfo=UTC), False),  # Sun 18:00 NY - weekly open
    ],
)
def test_broker_closed_follows_new_york_time_with_us_dst(utc, closed):
    assert rules.broker_closed(utc) is closed


def test_weekend_quotes_are_not_admitted():
    sat = datetime(2026, 10, 10, 12, tzinfo=UTC)
    tue = datetime(2026, 10, 6, 12, tzinfo=UTC)
    m5 = [Candle(sat, 1, 2, 0.5, 1.5), Candle(tue, 1, 2, 0.5, 1.5)]
    assert [c.t for c in rules.admit(m5)] == [tue]


def test_a_missing_trading_hour_is_a_data_gap_but_the_daily_break_is_not():
    day = datetime(2026, 10, 6, 19, tzinfo=UTC)  # Tue, EDT: break 21:00-22:00 UTC
    full = list(range(0, 60, 5))
    m5 = [*_hour(day, full), *_hour(day + H, full), *_hour(day + 3 * H, full)]  # 21:00 absent
    series = rules.H1Series.from_buckets(rules.aggregate_h1(rules.admit(m5)))
    assert series.gap_before == [False, False, False]
    m5_gap = [*_hour(day, full), *_hour(day + 3 * H, full)]  # 20:00 missing (open hour)
    series = rules.H1Series.from_buckets(rules.aggregate_h1(rules.admit(m5_gap)))
    assert series.gap_before == [False, True]


def test_a_partial_trading_hour_is_excluded_and_counts_as_a_gap():
    day = datetime(2026, 10, 6, 9, tzinfo=UTC)
    full = list(range(0, 60, 5))
    m5 = [*_hour(day, full), *_hour(day + H, full[:-2]), *_hour(day + 2 * H, full)]
    series = rules.H1Series.from_buckets(rules.aggregate_h1(m5))
    assert [b.t for b in series.bars] == [day, day + 2 * H]
    assert series.gap_before == [False, True]


# --- live prefix decisions -----------------------------------------------------
def test_scenario_waits_before_the_shift_and_qualifies_after_it():
    waiting = _evaluate(sc.history(sc.MSS_T), sc.MSS_T)
    assert waiting.outcome is Outcome.WAITING and waiting.setup.direction is Direction.BUY
    decided = _evaluate(sc.history(sc.MSS_T + M5), sc.MSS_T + M5 + timedelta(minutes=4))
    assert decided.outcome is Outcome.QUALIFIED
    assert decided.decided_at == sc.MSS_T + M5
    s = decided.setup
    assert (s.entry, round(s.sl, 3), s.tp1) == (2002.0, 1989.743, 2030.0)
    assert s.rr >= rules.MIN_RR and s.entry_basis == "fvg"
    assert {k.name for k in s.key_levels} >= {"previous_day_low"}


def test_a_decision_does_not_change_as_later_candles_arrive():
    early = _evaluate(sc.history(sc.MSS_T + M5), sc.MSS_T + M5)
    late = _evaluate(sc.history(), sc.EXPIRES_AT + timedelta(hours=2))
    def key(e):
        return (e.outcome, e.decided_at, e.setup.entry, e.setup.sl, e.setup.tp1)

    assert key(early) == key(late)


def test_a_missing_candle_after_the_decision_does_not_undo_it():
    """Codex review counterexample: 12:45 missing after a 12:30 decision."""
    m5 = [c for c in sc.history() if c.t != sc.RAID_CLOSE + timedelta(minutes=45)]
    ev = _evaluate(m5, sc.EXPIRES_AT + timedelta(hours=2))
    assert ev.outcome is Outcome.QUALIFIED and ev.decided_at == sc.MSS_T + M5


def test_a_missing_candle_before_the_shift_makes_it_data_incomplete():
    m5 = [c for c in sc.history() if c.t != sc.RAID_CLOSE + timedelta(minutes=15)]
    ev = _evaluate(m5, sc.EXPIRES_AT + timedelta(hours=2))
    assert ev.outcome is Outcome.REJECTED and ev.reason.startswith(rules.DATA_INCOMPLETE)


def test_no_shift_is_waiting_until_the_window_is_complete():
    """A raid whose M5 never shifts: WAITING mid-window, NO_MSS once the
    whole window exists, DATA_INCOMPLETE if the data stops before expiry."""
    flat = [c for c in sc.history() if c.t < sc.RAID_CLOSE]
    t = sc.RAID_CLOSE
    while t < sc.EXPIRES_AT + timedelta(minutes=10):
        flat.append(Candle(t, 1999.0, 1999.4, 1998.6, 1999.0))  # no swing high is broken
        t += M5
    mid = [c for c in flat if c.t < sc.RAID_CLOSE + H]
    assert _evaluate(mid, sc.RAID_CLOSE + H).outcome is Outcome.WAITING
    done = _evaluate(flat, sc.EXPIRES_AT + timedelta(minutes=10))
    assert done.outcome is Outcome.REJECTED and done.reason == Reason.NO_MSS
    stalled = _evaluate(mid, sc.EXPIRES_AT + rules.GRACE)
    assert stalled.outcome is Outcome.REJECTED and stalled.reason.startswith(rules.DATA_INCOMPLETE)


def test_an_incomplete_raid_hour_never_forms_a_setup():
    m5 = [c for c in sc.history() if c.t != sc.RAID_T + timedelta(minutes=30)]
    m5 = rules.admit(m5)
    series = rules.H1Series.from_buckets(rules.aggregate_h1(m5))
    assert sc.RAID_T not in [b.t for b in series.bars]


# --- key levels -------------------------------------------------------------------
def test_key_level_index_equals_frozen_v1_on_a_gap_free_series():
    m5 = rules.admit(sc.history())
    series = rules.H1Series.from_buckets(rules.aggregate_h1(m5))
    assert not any(series.gap_before)
    index = rules.KeyLevelIndex(series)
    bars = series.bars
    for r in range(16, len(bars)):
        tol = (v1rules.atr(bars, r) or 0.0) * 0.1
        for price in (bars[r].high, bars[r].low):
            expected = v1rules.key_levels_for(bars, r - 1, price, tol)
            assert index.levels(r - 1, price, tol) == expected


def test_trading_day_counts_the_sunday_open_as_monday():
    assert rules.trading_day(datetime(2026, 10, 11, 22, 30, tzinfo=UTC)) == date(2026, 10, 12)
    assert rules.trading_day(datetime(2026, 10, 12, 1, 0, tzinfo=UTC)) == date(2026, 10, 12)
    assert rules.trading_day(datetime(2026, 10, 9, 20, 0, tzinfo=UTC)) == date(2026, 10, 9)


def test_frozen_design_a_parameters():
    assert (rules.ANCHOR_TIMEFRAME, rules.MIN_RR, rules.EXPIRY_ANCHOR_CANDLES) == ("H1", 2.0, 3)
    assert (rules.MODELLED_SPREAD, rules.MAX_COST_FRACTION, rules.DAILY_CAP) == (0.26, 0.10, 3)


# --- research parity (untracked research checkout only) ---------------------------
def _research_dir() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "research" / "smc_ict_crt_v2_3signals"
        if (candidate / "v2_rules.py").exists():
            return candidate
    return None


@pytest.mark.skipif(_research_dir() is None, reason="research checkout not present")
def test_parity_with_frozen_research_design_a_on_broker_history():
    """Every decision live makes without a data gap matches the frozen
    research design A, except a small number whose key levels differ because
    live drops swing pivots that straddle a data gap; every live-qualified
    setup is research-qualified with identical levels."""
    research_dir = _research_dir()
    assert research_dir is not None
    # The frozen research v1 folder holds `backtest`; v2_rules imports it too.
    paths = [str(research_dir), str(research_dir.parent / "smc_ict_crt_v1")]
    sys.path[:0] = paths
    try:
        import backtest as v1backtest  # type: ignore[import-not-found]
        import v2_rules as research  # type: ignore[import-not-found]
    finally:
        for p in paths:
            sys.path.remove(p)
    m5_path = research.V1_DIR / "data_mt5_24m" / "XAUUSDc_M5.csv"
    if not m5_path.exists():
        pytest.skip("research data not present")
    raw = v1backtest.load(m5_path)
    times = [c.t for c in raw]
    start, end = datetime(2024, 9, 23, tzinfo=UTC), datetime(2100, 1, 1, tzinfo=UTC)
    ref = {c.setup.raid_t: c for c in research.generate(
        "H1", research.aggregate(raw, research.TIMEFRAMES["H1"]), raw, times, start, end, 2.0)}
    m5 = rules.admit([Candle(c.t, c.open, c.high, c.low, c.close) for c in raw])
    series = rules.H1Series.from_buckets(rules.aggregate_h1(m5))
    index = rules.KeyLevelIndex(series)
    live_times = [c.t for c in m5]
    decided = mismatched = 0
    for r in range(1, len(series.bars)):
        if not (start <= series.bars[r].t <= end):
            continue
        ev = rules.evaluate(series, index, r, m5, live_times, end)
        if ev is None or ev.reason.startswith(rules.DATA_INCOMPLETE):
            continue
        a = ref.get(ev.setup.raid_t)
        assert a is not None, f"live evaluated a raid research did not: {ev.setup.raid_t}"
        decided += 1
        live_label = "rr" if ev.outcome is Outcome.QUALIFIED else ev.reason
        research_label = "rr" if a.qualified else str(a.setup.reason)
        if ev.outcome is Outcome.QUALIFIED:
            assert a.qualified, ev.setup.raid_t
            assert (ev.setup.entry, ev.setup.sl, ev.setup.tp1, ev.setup.rr, ev.setup.mss_t) == (
                a.setup.entry, a.setup.sl, a.setup.tp1, a.setup.rr, a.setup.mss_t)
        mismatched += live_label != research_label
    assert decided > 7000
    assert mismatched / decided < 0.005  # 18 of ~7,300 measured (key levels across gaps)

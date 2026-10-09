"""smc-ict-crt-v2 design A - deterministic rules for a live prefix (ADR-185).

Design A of `research/smc_ict_crt_v2_3signals/SPEC.md` (pre-registered
2026-10-06): the frozen v1 CRT structure applied to **H1** ranges, minimum
R:R 2.0, three-H1-candle expiry, plus the two quality rules C10 (geometry)
and C11 (modelled spread <= 10% of the stop distance). That study's verdict
was "no acceptable v2"; this module implements the design the operator later
chose to run experimentally. It is not a validated strategy.

Every primitive (CRT test, ATR, fractal swings, MSS, FVG, OB, entry, stop,
target) is the frozen v1 module `app.services.smc_crt.rules`, imported and
called unchanged. What is new is how live data is admitted:

- **Broker hours.** Production reads Twelve Data, which quotes XAUUSD 24/7,
  including low-activity weekend quotes (median M5 range 0.25 vs ~3.6 on
  weekdays, 2026-08/10). The strategy was researched on the execution
  broker's (Exness) candles, which never exist while the broker is closed.
  `broker_closed` is that schedule - daily 17:00-18:00 New York time and the
  weekend from Friday 17:00 to Sunday 18:00 New York time - verified against
  541,441 Exness M5 candles 2019-01 to 2026-09: not one falls inside it.
  Candles inside those windows are not admitted; a hole there is not a gap.
- **Complete hours only.** `aggregate_h1` builds UTC-aligned H1 candles from
  admitted final M5 candles; a bucket is complete only with exactly the twelve
  on-grid stamps :00 ... :55. `H1Series` keeps complete buckets only, so a
  partial hour never feeds a range, ATR, swing or key level.
- **Data gaps.** Any missing candle outside the broker-closed windows is a
  data gap. A decision whose *own* inputs cross one is DATA_INCOMPLETE, never
  a setup built on missing data; a gap that comes after the decision does
  not undo it.
- **Live prefix.** With no M5 shift yet a setup *waits*, instead of being
  closed with NO_MSS the way the research backtest (which saw the whole
  window) did; NO_MSS is concluded only from a complete, gap-free window.

Pure functions only: candles in, decisions out. No database, no clock.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from app.services.smc_crt.rules import (
    ATR_PERIOD,
    FRACTAL_WINDOW,
    KEY_LEVEL_ATR_FRACTION,
    SL_BUFFER_ATR_FRACTION,
    SPREAD,
    Candle,
    Direction,
    KeyLevel,
    Reason,
    Setup,
    Swing,
    atr,
    crt_candidate,
    entry_level,
    find_fvg,
    find_mss,
    find_ob,
    session_of,
    stops_and_targets,
    swings_range,
)

# --- identity and frozen design-A parameters (research SPEC.md §2, §4 A) ----
STRATEGY_NAME = "smc_ict_crt_v2_a"
STRATEGY_VERSION = "smc-ict-crt-v2-a"
DESIGN = "A"
ANCHOR_TIMEFRAME = "H1"
ANCHOR = timedelta(hours=1)
M5 = timedelta(minutes=5)
H1_SLOTS = frozenset(range(0, 60, 5))
EXPIRY_ANCHOR_CANDLES = 3  # C9: three H1 candles after the raid closes
MIN_RR = 2.0  # C12 (design A)
#: C11 uses the *modelled* spread the study was frozen with (v1's P23, 0.26).
#: It is a decision rule, not a measurement of the broker's real spread.
MODELLED_SPREAD = SPREAD
MAX_COST_FRACTION = 0.10  # C11
DAILY_CAP = 3  # C14

#: Live data admission (not strategy thresholds). A data gap this far before
#: the raid still invalidates it - the previous day's range, the session
#: range, ATR(14) and the previous candle all lie inside it; and an undecided
#: setup may wait this long past expiry for late data.
DATA_LOOKBACK = timedelta(hours=48)
GRACE = timedelta(minutes=30)
#: `find_ob` looks back at most this many M5 candles from the MSS candle.
_OB_LOOKBACK = 30

REJECT_GEOMETRY = "REJECT_GEOMETRY"  # C10
REJECT_COST = "REJECT_COST"  # C11
DATA_INCOMPLETE = "DATA_INCOMPLETE"  # live only: decision inputs have a data gap


# --- the execution broker's hours ---------------------------------------------
def _us_dst(t: datetime) -> bool:
    """US daylight saving: 02:00 local on the second Sunday of March to 02:00
    local on the first Sunday of November (the rule in force since 2007)."""
    y = t.year
    start = datetime(y, 3, 8, tzinfo=UTC)
    start += timedelta(days=(6 - start.weekday()) % 7)
    end = datetime(y, 11, 1, tzinfo=UTC)
    end += timedelta(days=(6 - end.weekday()) % 7)
    return start + timedelta(hours=7) <= t < end + timedelta(hours=6)


def broker_closed(t: datetime) -> bool:
    """Whether the execution broker's XAUUSD market is closed at UTC time `t`.

    Daily 17:00-18:00 New York time, and Friday 17:00 to Sunday 18:00 New
    York time. Verified: none of 541,441 Exness XAUUSDc M5 candles
    (2019-01-02 to 2026-09-23) falls inside these windows. Holidays and the
    broker's other irregular closures are not modelled - a candle missing
    then is treated as a data gap, the conservative side."""
    ny = t.astimezone(UTC) - timedelta(hours=4 if _us_dst(t.astimezone(UTC)) else 5)
    wd, h = ny.weekday(), ny.hour
    if wd == 5 or (wd == 4 and h >= 17) or (wd == 6 and h < 18):
        return True
    return h == 17


def admit(m5: Sequence[Candle]) -> list[Candle]:
    """The M5 candles the strategy may use: those of broker-open periods."""
    return [c for c in m5 if not broker_closed(c.t)]


def _only_closures_between(after: datetime, before: datetime, step: timedelta) -> bool:
    """Every `step` slot strictly between two present ones is broker-closed."""
    t = after + step
    while t < before:
        if not broker_closed(t):
            return False
        t += step
    return True


# --- H1 from M5 --------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class H1Bar:
    candle: Candle
    #: Exactly the twelve on-grid M5 timestamps of the hour were present.
    complete: bool

    @property
    def t(self) -> datetime:
        return self.candle.t


def aggregate_h1(m5: Sequence[Candle]) -> list[H1Bar]:
    """UTC-aligned H1 buckets from M5 candles sorted by time.

    First open, highest high, lowest low, last close - the aggregation that
    rebuilds the broker's H4 exactly in the research data. A bucket is
    complete only if its M5 stamps are exactly {:00, :05, ... :55}: no
    duplicate, nothing off the five-minute grid, no hole."""
    out: list[H1Bar] = []
    group: list[Candle] = []

    def flush() -> None:
        if not group:
            return
        t = group[0].t.replace(minute=0, second=0, microsecond=0)
        minutes = [c.t.minute for c in group]
        on_grid = all(c.t.second == 0 and c.t.microsecond == 0 and c.t.minute % 5 == 0
                      for c in group)
        complete = on_grid and len(minutes) == len(H1_SLOTS) and set(minutes) == H1_SLOTS
        out.append(H1Bar(Candle(t, group[0].open, max(c.high for c in group),
                                min(c.low for c in group), group[-1].close), complete))

    for c in m5:
        hour = c.t.replace(minute=0, second=0, microsecond=0)
        if group and group[0].t.replace(minute=0, second=0, microsecond=0) != hour:
            flush()
            group = []
        group.append(c)
    flush()
    return out


@dataclass(slots=True)
class H1Series:
    """Complete H1 candles only, with whether a data gap precedes each one."""

    bars: list[Candle]
    #: `gap_before[i]`: a **data gap** lies between bars[i-1] and bars[i] -
    #: an hour outside the broker-closed windows that is missing or partial.
    gap_before: list[bool]

    @classmethod
    def from_buckets(cls, buckets: Sequence[H1Bar]) -> H1Series:
        bars = [b.candle for b in buckets if b.complete]
        gaps = [False] * len(bars)
        for i in range(1, len(bars)):
            if bars[i].t - bars[i - 1].t != ANCHOR:
                gaps[i] = not _only_closures_between(bars[i - 1].t, bars[i].t, ANCHOR)
        return cls(bars, gaps)

    def gap_between(self, lo: int, hi: int) -> bool:
        """A data gap anywhere between bars[lo] and bars[hi]."""
        return any(self.gap_before[j] for j in range(max(1, lo + 1), hi + 1))


class KeyLevelIndex:
    """v1's `key_levels_for` (P10/P11), precomputed: same levels, same order.

    v1's function rescans every earlier candle on each call; on H1 that is
    quadratic. Level names are v1's verbatim ("previous_h4_*" names the
    previous *anchor* candle) so a record reads like v1's. Swing pivots whose
    five-candle window crosses a data gap are dropped: across a gap the
    neighbours are not real neighbours."""

    def __init__(self, series: H1Series) -> None:
        self.c = series.bars
        pivots: list[Swing] = [
            s for s in swings_range(self.c, 0, len(self.c) - 1)
            if not series.gap_between(s.index - FRACTAL_WINDOW, s.index + FRACTAL_WINDOW)
        ]
        self.pivots = sorted(pivots, key=lambda s: s.price)
        self.pivot_prices = [s.price for s in self.pivots]
        self.day_range: dict[date, tuple[float, float]] = {}
        for x in self.c:
            d = x.t.date()
            hi, lo = self.day_range.get(d, (x.high, x.low))
            self.day_range[d] = (max(hi, x.high), min(lo, x.low))
        self.days = sorted(self.day_range)
        self.session_before: list[tuple[float, float] | None] = []
        running: dict[tuple[date, str], tuple[float, float]] = {}
        for x in self.c:
            k = (x.t.date(), session_of(x.t))
            self.session_before.append(running.get(k))
            hi, lo = running.get(k, (x.high, x.low))
            running[k] = (max(hi, x.high), min(lo, x.low))

    def levels(self, anchor_index: int, price: float, tolerance: float) -> list[KeyLevel]:
        found: list[KeyLevel] = []
        anchor = self.c[anchor_index]

        def add(name: str, level: float) -> None:
            d = abs(level - price)
            if d <= tolerance:
                found.append(KeyLevel(name, level, round(d, 5)))

        if anchor_index >= 1:
            add("previous_h4_high", self.c[anchor_index - 1].high)
            add("previous_h4_low", self.c[anchor_index - 1].low)
        k = bisect_left(self.days, anchor.t.date())
        if k > 0:  # the latest earlier date; all its candles precede the anchor
            hi, lo = self.day_range[self.days[k - 1]]
            add("previous_day_high", hi)
            add("previous_day_low", lo)
        lo_i = bisect_left(self.pivot_prices, price - tolerance)
        hi_i = bisect_right(self.pivot_prices, price + tolerance)
        near = sorted(
            (s for s in self.pivots[lo_i:hi_i] if s.index <= anchor_index - 1 - FRACTAL_WINDOW),
            key=lambda s: (s.index, 0 if s.high else 1),
        )
        for s in near:
            add("swing_high" if s.high else "swing_low", s.price)
        sess = self.session_before[anchor_index]
        if sess is not None:
            add("session_high", sess[0])
            add("session_low", sess[1])
        return sorted(found, key=lambda kl: kl.distance)


def m5_gap_between(m5: Sequence[Candle], lo: int, hi: int) -> bool:
    """A data gap (not a broker closure) between m5[lo] and m5[hi]."""
    for j in range(max(1, lo + 1), hi + 1):
        prev, cur = m5[j - 1].t, m5[j].t
        if cur - prev != M5 and not _only_closures_between(prev, cur, M5):
            return True
    return False


# --- the decision -------------------------------------------------------------
class Outcome(StrEnum):
    WAITING = "waiting"  # not decidable yet with the data available
    REJECTED = "rejected"  # terminal, with a reason
    QUALIFIED = "qualified"  # every rule passed; publication is the service's call


@dataclass(slots=True)
class Evaluation:
    outcome: Outcome
    setup: Setup
    reason: str = ""
    #: The stage reached, in the research study's names: crt | close_back |
    #: key_level | mss | entry | geometry | cost | rr.
    stage: str = ""
    mss_index: int | None = None
    #: When the deciding M5 candle closed - the earliest moment the decision
    #: could exist. Publication time is recorded separately by the service.
    decided_at: datetime | None = None


def _data(setup: Setup, why: str, stage: str) -> Evaluation:
    return Evaluation(Outcome.REJECTED, setup, f"{DATA_INCOMPLETE}: {why}", stage)


def evaluate(
    series: H1Series,
    index: KeyLevelIndex,
    r: int,
    m5: list[Candle],
    m5_times: Sequence[datetime],
    now: datetime,
) -> Evaluation | None:
    """SPEC §2 design A for raid candle `series.bars[r]`, on what exists now.

    `m5` must be admitted (`admit`) final candles (the service applies D9).
    Returns None when the pair is not a CRT candidate at all (no one-sided
    sweep).

    - H1 inputs crossing a data gap, or too little history -> DATA_INCOMPLETE.
    - The first M5 shift is searched on what exists. If it is found, the
      decision stands when the candles it used - the confirmation window up
      to the shift, ATR(14) and the order-block lookback - have no data gap;
      a gap after it does not matter.
    - No shift yet -> WAITING, until the whole research window exists with no
      data gap (-> NO_MSS), or `now` passes expiry plus GRACE without that
      (-> DATA_INCOMPLETE).
    """
    bars = series.bars
    if r < 1 or r >= len(bars):
        return None
    setup = crt_candidate(bars, r)  # frozen v1 CRT test, anchor = r - 1
    if setup is None:
        return None
    setup.news_data_available, setup.high_impact_event = False, "unknown"
    raid = bars[r]
    if r < ATR_PERIOD + 1:
        return _data(setup, "not enough H1 history", "crt")
    first = bisect_left([b.t for b in bars], raid.t - DATA_LOOKBACK)
    if series.gap_between(min(first, r - ATR_PERIOD), r):
        return _data(setup, "H1 data gap before the raid", "crt")

    tolerance_atr = atr(bars, r, ATR_PERIOD)
    assert tolerance_atr is not None
    setup.key_levels = index.levels(r - 1, setup.raid_extreme or 0.0,
                                    tolerance_atr * KEY_LEVEL_ATR_FRACTION)
    setup.key_level_ok = bool(setup.key_levels)
    if not setup.closed_back_inside:
        return Evaluation(Outcome.REJECTED, setup, Reason.NO_CLOSE_BACK_INSIDE, "crt")
    if not setup.key_level_ok:
        return Evaluation(Outcome.REJECTED, setup, Reason.KEY_LEVEL_UNCERTAIN, "close_back")

    raid_close = raid.t + ANCHOR
    expires_at = raid_close + EXPIRY_ANCHOR_CANDLES * ANCHOR
    setup.expires_at = expires_at
    i0 = bisect_left(m5_times, raid_close)
    i1 = bisect_left(m5_times, expires_at)
    if i0 >= len(m5):
        if now >= expires_at + GRACE:
            return _data(setup, "no M5 candles after the raid", "key_level")
        return Evaluation(Outcome.WAITING, setup, "waiting for the M5 shift", "key_level")
    if i0 < ATR_PERIOD or m5_gap_between(m5, i0 - ATR_PERIOD, i0) or (
        m5[i0].t != raid_close and not _only_closures_between(raid_close - M5, m5[i0].t, M5)
    ):
        return _data(setup, "M5 data gap at the raid close", "key_level")
    end = min(i1, len(m5) - 1)
    buy = setup.direction is Direction.BUY
    mss = find_mss(m5, i0, end, setup.direction)  # C5
    if mss is None:
        if m5_gap_between(m5, i0, end):
            if i1 < len(m5) or now >= expires_at + GRACE:
                return _data(setup, "M5 data gap in the confirmation window", "key_level")
            return Evaluation(Outcome.WAITING, setup, "waiting for the M5 shift", "key_level")
        if i1 < len(m5):  # the whole research window exists, gap-free
            return Evaluation(Outcome.REJECTED, setup, Reason.NO_MSS, "key_level")
        if now >= expires_at + GRACE:
            return _data(setup, "M5 data stopped before expiry", "key_level")
        return Evaluation(Outcome.WAITING, setup, "waiting for the M5 shift", "key_level")
    mss_index, mss_level = mss
    # Causal inputs only: the window up to the shift, ATR(14) at it and the
    # order-block lookback. A candle missing after the shift is irrelevant.
    if m5_gap_between(m5, min(i0 - ATR_PERIOD, mss_index - _OB_LOOKBACK), mss_index):
        return _data(setup, "M5 data gap before the shift", "key_level")
    setup.mss_t, setup.mss_level = m5[mss_index].t, mss_level
    setup.displacement_from = m5[i0].t
    setup.fvg = find_fvg(m5, i0, mss_index, setup.direction)
    setup.ob = find_ob(m5, mss_index, setup.direction)
    decided_at = m5[mss_index].t + M5
    level = entry_level(setup)  # C6
    if level is None:
        return Evaluation(Outcome.REJECTED, setup, Reason.NO_RETEST, "mss", mss_index, decided_at)
    setup.entry, setup.entry_basis = level

    m5_atr = atr(m5, mss_index, ATR_PERIOD) or 0.0
    pivots = [s for s in swings_range(m5, max(0, i0 - 2 * FRACTAL_WINDOW), mss_index)
              if s.high != buy]
    stops_and_targets(setup, m5_atr * SL_BUFFER_ATR_FRACTION,
                      pivots[-1].price if pivots else None)  # C7, C8
    setup.tp2 = None  # v1's recorded-only TP2 is not part of design A
    assert setup.sl is not None and setup.tp1 is not None
    valid = setup.sl < setup.entry < setup.tp1 if buy else setup.tp1 < setup.entry < setup.sl
    if not valid:
        return Evaluation(Outcome.REJECTED, setup, REJECT_GEOMETRY, "entry", mss_index, decided_at)
    if MODELLED_SPREAD > MAX_COST_FRACTION * (setup.sl_distance or 0.0):
        return Evaluation(Outcome.REJECTED, setup, REJECT_COST, "geometry", mss_index, decided_at)
    if setup.rr is None or setup.rr < MIN_RR:
        return Evaluation(Outcome.REJECTED, setup, Reason.REJECT_RR, "cost", mss_index, decided_at)
    return Evaluation(Outcome.QUALIFIED, setup, "", "rr", mss_index, decided_at)


def trading_day(t: datetime) -> date:
    """C14 / research SPEC §5: the broker (UTC) date; the Sunday open counts
    as Monday."""
    d = t.astimezone(UTC).date()
    return d + timedelta(days=1) if d.weekday() == 6 else d


__all__ = [
    "ANCHOR", "ANCHOR_TIMEFRAME", "DAILY_CAP", "DATA_INCOMPLETE", "DESIGN",
    "EXPIRY_ANCHOR_CANDLES", "GRACE", "MAX_COST_FRACTION", "MIN_RR", "MODELLED_SPREAD",
    "REJECT_COST", "REJECT_GEOMETRY", "STRATEGY_NAME", "STRATEGY_VERSION",
    "Evaluation", "H1Bar", "H1Series", "KeyLevelIndex", "Outcome", "admit",
    "aggregate_h1", "broker_closed", "evaluate", "m5_gap_between", "trading_day",
]

"""smc-ict-crt-v1 - frozen deterministic rules (research only).

Nothing here imports the backend app, touches a database or reaches a
broker. Every function is pure: candles in, values out, so the same inputs
always give the same decision. See SPEC.md for the frozen parameters (P1-P25)
referenced in the comments.

No look-ahead anywhere: a swing pivot exists only once its right-hand bars
have closed, and every decision at bar i uses bars <= i only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

# --- frozen parameters (SPEC.md §2) ---------------------------------------
FRACTAL_WINDOW = 2  # P1/P2
KEY_LEVEL_ATR_FRACTION = 0.10  # P10
SL_BUFFER_ATR_FRACTION = 0.10  # P14
MIN_RR = 2.0  # P18
EXPIRY_HOURS = 12  # P19
MAX_OPEN_TRADES = 1  # P20
SPREAD = 0.26  # P23
ATR_PERIOD = 14


class Direction(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Decision(StrEnum):
    WAIT = "WAIT"
    REJECT = "REJECT"
    BUY = "BUY"
    SELL = "SELL"
    EXPIRED = "EXPIRED"


class Reason(StrEnum):
    KEY_LEVEL_UNCERTAIN = "KEY_LEVEL_UNCERTAIN"
    NO_CLOSE_BACK_INSIDE = "NO_CLOSE_BACK_INSIDE"
    NO_MSS = "NO_MSS"
    NO_RETEST = "NO_RETEST"
    REJECT_RR = "REJECT_RR"
    REJECT_OPEN_TRADE = "REJECT_OPEN_TRADE"
    SETUP_EXPIRED = "SETUP_EXPIRED"


@dataclass(frozen=True, slots=True)
class Candle:
    t: datetime
    open: float
    high: float
    low: float
    close: float
    spread_points: int = 0

    @property
    def bullish(self) -> bool:
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        return self.close < self.open


@dataclass(frozen=True, slots=True)
class Swing:
    index: int
    t: datetime
    price: float
    high: bool  # True = swing high, False = swing low


@dataclass(frozen=True, slots=True)
class Zone:
    """An FVG or an Order Block. `proximal` is the edge price reaches first."""

    kind: str  # "fvg" | "ob"
    direction: Direction
    high: float
    low: float
    t: datetime

    @property
    def proximal(self) -> float:
        # A BUY retraces down into the zone, so its top is touched first.
        return self.high if self.direction is Direction.BUY else self.low


@dataclass(frozen=True, slots=True)
class KeyLevel:
    name: str
    price: float
    distance: float


@dataclass(slots=True)
class Setup:
    """One evaluated CRT setup, with every field the logging spec requires."""

    symbol: str
    direction: Direction
    anchor_t: datetime
    crt_high: float
    crt_low: float
    raid_t: datetime | None = None
    raid_high: float | None = None
    raid_low: float | None = None
    raid_extreme: float | None = None
    closed_back_inside: bool = False
    key_levels: list[KeyLevel] = field(default_factory=list)
    key_level_ok: bool = False
    liquidity_side: str = ""
    h4_context: str = ""
    equilibrium: float | None = None
    location: str = ""  # premium | discount | equilibrium
    session: str = ""
    mss_t: datetime | None = None
    mss_level: float | None = None
    displacement_from: datetime | None = None
    fvg: Zone | None = None
    ob: Zone | None = None
    entry_basis: str = ""
    entry: float | None = None
    entry_t: datetime | None = None
    sl: float | None = None
    sl_basis: str = ""
    sl_distance: float | None = None
    sl_buffer: float | None = None
    sl_alt: float | None = None
    rr_alt: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    rr: float | None = None
    expires_at: datetime | None = None
    news_data_available: bool = False
    high_impact_event: str = "unknown"
    decision: Decision = Decision.WAIT
    reason: str = ""
    outcome: str = ""
    exit_price: float | None = None
    exit_t: datetime | None = None
    gross_r: float | None = None
    net_r: float | None = None
    mae_r: float | None = None


# --- primitives ------------------------------------------------------------
def true_range(prev_close: float, c: Candle) -> float:
    return max(c.high - c.low, abs(c.high - prev_close), abs(c.low - prev_close))


def atr(candles: list[Candle], end: int, period: int = ATR_PERIOD) -> float | None:
    """Simple ATR over the `period` candles ending at `end` (inclusive).

    Deliberately uses only closed candles at or before `end`."""
    if end < period:
        return None
    trs = [true_range(candles[i - 1].close, candles[i]) for i in range(end - period + 1, end + 1)]
    return sum(trs) / len(trs)


def swings_range(
    candles: list[Candle], lo: int, hi: int, window: int = FRACTAL_WINDOW
) -> list[Swing]:
    """Confirmed pivots whose index lies in [lo + window, hi - window].

    Identical to `swings(candles, hi)` restricted to that index range - a
    pivot only ever depends on its own `window` neighbours either side, so
    starting the scan later cannot change which pivots are found. This exists
    purely so long histories do not rescan from bar 0 for every bar; it is a
    speed detail, not a rule (SPEC P1/P2 unchanged)."""
    out: list[Swing] = []
    for i in range(max(window, lo + window), hi - window + 1):
        mid = candles[i]
        left = candles[i - window:i]
        right = candles[i + 1:i + 1 + window]
        if len(right) < window:
            break
        if all(mid.high > c.high for c in left) and all(mid.high > c.high for c in right):
            out.append(Swing(i, mid.t, mid.high, True))
        if all(mid.low < c.low for c in left) and all(mid.low < c.low for c in right):
            out.append(Swing(i, mid.t, mid.low, False))
    return out


def swings(candles: list[Candle], end: int, window: int = FRACTAL_WINDOW) -> list[Swing]:
    """Confirmed fractal pivots in candles[0..end] (P1/P2).

    A pivot at i needs `window` bars either side, so the newest pivot that
    can exist is at `end - window` - never later, which is what keeps this
    free of look-ahead."""
    out: list[Swing] = []
    for i in range(window, max(window, end - window + 1)):
        mid = candles[i]
        left = candles[i - window:i]
        right = candles[i + 1:i + 1 + window]
        if len(right) < window:
            break
        if all(mid.high > c.high for c in left) and all(mid.high > c.high for c in right):
            out.append(Swing(i, mid.t, mid.high, True))
        if all(mid.low < c.low for c in left) and all(mid.low < c.low for c in right):
            out.append(Swing(i, mid.t, mid.low, False))
    return out


def session_of(t: datetime) -> str:
    """P21 - recorded, never a filter."""
    h = t.astimezone(UTC).hour
    if 0 <= h < 7:
        return "asia"
    if 7 <= h < 12:
        return "london"
    if 12 <= h < 16:
        return "london_ny_overlap"
    if 16 <= h < 21:
        return "new_york"
    return "outside"


# --- CRT on H4 -------------------------------------------------------------
def key_levels_for(
    h4: list[Candle], anchor_index: int, price: float, tolerance: float
) -> list[KeyLevel]:
    """Objective levels within `tolerance` of `price` (P10/P11).

    Only data available at the anchor is used: earlier H4 candles, the
    previous day's range, confirmed H4 swings and the anchor's session."""
    found: list[KeyLevel] = []
    anchor = h4[anchor_index]

    def add(name: str, level: float) -> None:
        d = abs(level - price)
        if d <= tolerance:
            found.append(KeyLevel(name, level, round(d, 5)))

    if anchor_index >= 1:
        add("previous_h4_high", h4[anchor_index - 1].high)
        add("previous_h4_low", h4[anchor_index - 1].low)

    day = anchor.t.date()
    prev_day = [c for c in h4[:anchor_index] if c.t.date() < day]
    if prev_day:
        last_day = max(c.t.date() for c in prev_day)
        bars = [c for c in prev_day if c.t.date() == last_day]
        add("previous_day_high", max(c.high for c in bars))
        add("previous_day_low", min(c.low for c in bars))

    for s in swings(h4, anchor_index - 1):
        add("swing_high" if s.high else "swing_low", s.price)

    same_session = [c for c in h4[:anchor_index] if c.t.date() == day and session_of(c.t) == session_of(anchor.t)]
    if same_session:
        add("session_high", max(c.high for c in same_session))
        add("session_low", min(c.low for c in same_session))

    return sorted(found, key=lambda k: k.distance)


def crt_candidate(h4: list[Candle], raid_index: int) -> Setup | None:
    """The CRT test on the candle *after* a closed anchor (rules §3-§5).

    Anchor = h4[raid_index - 1], both closed. A raid that never closes back
    inside the anchor's range is not a CRT - it is recorded with
    NO_CLOSE_BACK_INSIDE by the caller, never silently dropped."""
    if raid_index < 1 or raid_index >= len(h4):
        return None
    anchor, raid = h4[raid_index - 1], h4[raid_index]

    swept_low = raid.low < anchor.low
    swept_high = raid.high > anchor.high
    if swept_low == swept_high:  # neither, or both (inside bar / outside bar)
        return None

    direction = Direction.BUY if swept_low else Direction.SELL
    setup = Setup(
        symbol="XAUUSD", direction=direction, anchor_t=anchor.t,
        crt_high=anchor.high, crt_low=anchor.low, raid_t=raid.t,
        raid_high=raid.high, raid_low=raid.low,
        raid_extreme=raid.low if swept_low else raid.high,
        liquidity_side="sell_side" if swept_low else "buy_side",
        session=session_of(raid.t),
        expires_at=raid.t + timedelta(hours=4 + EXPIRY_HOURS),
    )
    setup.closed_back_inside = (
        raid.close > anchor.low if swept_low else raid.close < anchor.high
    )
    setup.equilibrium = (anchor.high + anchor.low) / 2
    ref = raid.close
    setup.location = (
        "discount" if ref < setup.equilibrium else "premium" if ref > setup.equilibrium else "equilibrium"
    )
    setup.h4_context = f"anchor {anchor.low:.3f}-{anchor.high:.3f}, raid close {raid.close:.3f}"
    return setup


# --- M5 confirmation -------------------------------------------------------
def find_mss(
    m5: list[Candle], start: int, end: int, direction: Direction
) -> tuple[int, float] | None:
    """First M5 close beyond the relevant confirmed swing (P3/P4).

    Walks bars start..end in order. At each bar only swings confirmed by
    then are considered (index <= i - FRACTAL_WINDOW), so the level cannot be
    chosen with hindsight."""
    last = min(end, len(m5) - 1)
    # Pivots are computed once over the window instead of rescanning history
    # for every bar; `swings_range` returns exactly the same pivots.
    pivots = [s for s in swings_range(m5, max(0, start - 2 * FRACTAL_WINDOW), last)
              if s.index >= start - FRACTAL_WINDOW and s.high == (direction is Direction.BUY)]
    for i in range(start, last + 1):
        confirmed = [s for s in pivots if s.index <= i - FRACTAL_WINDOW]
        if not confirmed:
            continue
        level = confirmed[-1].price
        if direction is Direction.BUY and m5[i].close > level:
            return i, level
        if direction is Direction.SELL and m5[i].close < level:
            return i, level
    return None


def find_fvg(m5: list[Candle], start: int, end: int, direction: Direction) -> Zone | None:
    """Newest 3-candle FVG inside the displacement leg (P6)."""
    newest: Zone | None = None
    for i in range(max(start, 2), end + 1):
        c1, c3 = m5[i - 2], m5[i]
        if direction is Direction.BUY and c1.high < c3.low:
            newest = Zone("fvg", direction, c3.low, c1.high, c3.t)
        elif direction is Direction.SELL and c1.low > c3.high:
            newest = Zone("fvg", direction, c1.low, c3.high, c3.t)
    return newest


def find_ob(m5: list[Candle], mss_index: int, direction: Direction) -> Zone | None:
    """Last opposing-direction candle before the displacement (P7)."""
    for i in range(mss_index, max(mss_index - 30, 0) - 1, -1):
        c = m5[i]
        if direction is Direction.BUY and c.bearish:
            return Zone("ob", direction, c.high, c.low, c.t)
        if direction is Direction.SELL and c.bullish:
            return Zone("ob", direction, c.high, c.low, c.t)
    return None


def entry_level(setup: Setup) -> tuple[float, str] | None:
    """FVG, else OB, else the MSS level (P8)."""
    if setup.fvg is not None:
        return setup.fvg.proximal, "fvg"
    if setup.ob is not None:
        return setup.ob.proximal, "ob"
    if setup.mss_level is not None:
        return setup.mss_level, "mss_retest"
    return None


def stops_and_targets(setup: Setup, buffer: float, mss_swing: float | None) -> None:
    """SL (P13/P14), the recorded alternative (P15), TP1 (P16) and RR (P18)."""
    assert setup.entry is not None and setup.raid_extreme is not None
    if setup.direction is Direction.BUY:
        setup.sl = setup.raid_extreme - buffer
        setup.tp1 = setup.crt_high
        setup.sl_alt = (mss_swing - buffer) if mss_swing is not None else None
    else:
        setup.sl = setup.raid_extreme + buffer
        setup.tp1 = setup.crt_low
        setup.sl_alt = (mss_swing + buffer) if mss_swing is not None else None
    setup.sl_basis = "h4_raid_extreme"
    setup.sl_buffer = buffer
    setup.sl_distance = abs(setup.entry - setup.sl)
    reward = abs(setup.tp1 - setup.entry)
    setup.rr = round(reward / setup.sl_distance, 3) if setup.sl_distance else None
    if setup.sl_alt is not None:
        alt_risk = abs(setup.entry - setup.sl_alt)
        setup.rr_alt = round(reward / alt_risk, 3) if alt_risk else None

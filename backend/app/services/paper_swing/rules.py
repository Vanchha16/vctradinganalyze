"""The swing strategy's rules, frozen for the paper-trading period (ADR-182).

A straight port of the ADR-181 backtest. **Do not change a rule, a
constant or an order of checks here during the paper period** unless it is
a technical bug: the point of the period is to test these exact rules on
data they have not seen, and a paper record produced by different rules
cannot be compared with the backtest. A deliberate change is a new
`STRATEGY_VERSION` and a new ADR.

Pure functions over plain bars - no database, no clock - so the same code
can be replayed over exported candles to check it still reproduces the
backtest.

- **D1 trend:** the last closed D1 close above EMA50, and EMA50 higher than
  five days earlier = up (mirror = down); anything else, no trade.
- **H4 swing:** a fractal pivot, three bars each side, known three bars
  after it forms.
- **Buy:** D1 up; the swing low just confirmed came after the latest swing
  high (the pullback), and sits above the swing low before that high (a
  higher low). Entry at the close of the confirming bar, stop 0.1 x ATR14
  below the swing low, target the swing high. Sell mirrors it.
- **Filter:** R:R >= 2 and stop >= 0.5 x ATR14 (the live risk engine's
  rules).
- **Exit:** stop or target, stop first when one bar touches both; closed at
  the market after 20 days.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

STRATEGY_VERSION = "swing-v1"
SETUP_NAME = "D1 EMA50 trend + H4 pullback"

H4 = timedelta(hours=4)
D1 = timedelta(days=1)

PIVOT_BARS = 3
STOP_BUFFER_ATR = 0.1
MIN_RISK_REWARD = 2.0
MIN_STOP_ATR = 0.5
MAX_HOLD = timedelta(days=20)
EMA_PERIOD = 50
EMA_SLOPE_BARS = 5
ATR_PERIOD = 14
ADR_PERIOD = 14
#: The backtest started trading only once this much history existed.
MIN_H4_BARS = 60
MIN_D1_BARS = 56

Direction = Literal["buy", "sell"]
Trend = Literal["up", "down"]
Decision = Literal["taken", "rr_below_min", "stop_below_min", "no_room"]
Outcome = Literal["win", "loss", "timeout"]


@dataclass(frozen=True)
class PairSpec:
    symbol: str
    name: str
    base_currency: str
    quote_currency: str
    pip: float
    #: Costs charged to every paper trade, so the paper result is net like
    #: the backtest's: the median spread on the operator's broker, and its
    #: swap per night held (2026-09-19 rates; indicative, rates change).
    spread_pips: float
    swap_long_pips: float
    swap_short_pips: float


PAIRS: tuple[PairSpec, ...] = (
    PairSpec("EURUSD", "Euro / US Dollar", "EUR", "USD", 0.0001, 0.8, -0.58, 0.0),
    PairSpec("GBPUSD", "British Pound / US Dollar", "GBP", "USD", 0.0001, 1.0, -0.21, -0.06),
    PairSpec("USDJPY", "US Dollar / Japanese Yen", "USD", "JPY", 0.01, 1.0, 0.0, 0.0),
)


@dataclass(frozen=True)
class Bar:
    """One candle. `time` is when it opened."""

    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Setup:
    direction: Direction
    d1_trend: Trend
    #: When the bar that confirmed the pullback closed - the decision time
    #: and, for a taken trade, the entry time.
    signal_time: datetime
    #: Open time of the pullback swing bar - with the direction, what makes
    #: a setup unique.
    pivot_time: datetime
    #: Open time of the swing the pullback came from (the target).
    origin_time: datetime
    pullback_level: float
    entry: float
    stop: float
    target: float
    risk: float
    reward: float
    risk_reward: float
    atr: float
    decision: Decision


@dataclass(frozen=True)
class Exit:
    outcome: Outcome
    price: float
    #: When the bar the exit happened in closed.
    time: datetime


def ema(values: Sequence[float], period: int) -> list[float]:
    out: list[float] = []
    k = 2 / (period + 1)
    current: float | None = None
    for value in values:
        current = value if current is None else value * k + current * (1 - k)
        out.append(current)
    return out


def atr(bars: Sequence[Bar], period: int = ATR_PERIOD) -> list[float]:
    """Wilder's ATR, seeded with the first bar's range."""
    out: list[float] = []
    current: float | None = None
    for i, bar in enumerate(bars):
        if i == 0:
            true_range = bar.high - bar.low
        else:
            prev_close = bars[i - 1].close
            true_range = max(
                bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)
            )
        current = true_range if current is None else (current * (period - 1) + true_range) / period
        out.append(current)
    return out


def pivots(bars: Sequence[Bar], k: int) -> tuple[list[int], list[int]]:
    """Indices of swing highs and swing lows: the extreme of the `k` bars
    either side, strictly beyond the `k` before it (so a flat top counts
    once, at its first bar)."""
    highs: list[int] = []
    lows: list[int] = []
    for i in range(k, len(bars) - k):
        window = bars[i - k : i + k + 1]
        before = window[:k]
        if bars[i].high == max(b.high for b in window) and all(
            bars[i].high > b.high for b in before
        ):
            highs.append(i)
        if bars[i].low == min(b.low for b in window) and all(bars[i].low < b.low for b in before):
            lows.append(i)
    return highs, lows


def closed_bars(bars: Sequence[Bar], length: timedelta, now: datetime) -> list[Bar]:
    """Only the bars that had closed by `now` - the provider also returns
    the one still forming, which no rule may see."""
    return [b for b in bars if b.time + length <= now]


def d1_trend(d1: Sequence[Bar]) -> Trend | None:
    """The trend on the last of `d1`, which must all be closed bars."""
    if len(d1) < MIN_D1_BARS:
        return None
    closes = [b.close for b in d1]
    line = ema(closes, EMA_PERIOD)
    i = len(d1) - 1
    if closes[i] > line[i] and line[i] > line[i - EMA_SLOPE_BARS]:
        return "up"
    if closes[i] < line[i] and line[i] < line[i - EMA_SLOPE_BARS]:
        return "down"
    return None


def average_daily_range(d1: Sequence[Bar], pip: float, period: int = ADR_PERIOD) -> float | None:
    """ADR: the mean high-low range of the last `period` closed D1 bars, in
    pips. Recorded on every setup; not a rule."""
    if len(d1) < period:
        return None
    recent = d1[-period:]
    return sum(b.high - b.low for b in recent) / period / pip


def setups_at(h4: Sequence[Bar], d1: Sequence[Bar], j: int) -> list[Setup]:
    """Every setup decided when H4 bar `j` closed.

    `h4` must hold closed bars only, `d1` the D1 bars closed by the time
    bar `j` closed. Pivots are computed on `h4[: j + 1]`, so nothing after
    bar `j` can leak in. A setup whose stop or target is on the wrong side
    of the entry is still returned, as `no_room`, so every candidate is
    on record.
    """
    if j < MIN_H4_BARS or j >= len(h4):
        return []
    bars = h4[: j + 1]
    confirmed = j - PIVOT_BARS
    swing_highs, swing_lows = pivots(bars, PIVOT_BARS)
    trend = d1_trend(d1)
    if trend is None:
        return []
    atr_now = atr(bars)[j]
    signal_time = bars[j].time + H4

    found: list[Setup] = []
    directions: tuple[Direction, ...] = ("buy", "sell")
    for direction in directions:
        is_buy = direction == "buy"
        same, opposite = (swing_lows, swing_highs) if is_buy else (swing_highs, swing_lows)
        if confirmed not in same:
            continue
        if trend != ("up" if is_buy else "down"):
            continue
        origins = [p for p in opposite if p < confirmed]
        if not origins:
            continue
        origin = origins[-1]
        earlier = [p for p in same if p < origin]
        if not earlier:
            continue
        entry = bars[j].close
        if is_buy:
            target, level = bars[origin].high, bars[confirmed].low
            if level <= bars[earlier[-1]].low:
                continue  # a lower low: the structure is broken, not a pullback
            stop = level - STOP_BUFFER_ATR * atr_now
            risk, reward = entry - stop, target - entry
        else:
            target, level = bars[origin].low, bars[confirmed].high
            if level >= bars[earlier[-1]].high:
                continue
            stop = level + STOP_BUFFER_ATR * atr_now
            risk, reward = stop - entry, entry - target

        decision: Decision
        if risk <= 0 or reward <= 0:
            decision, risk_reward = "no_room", 0.0
        else:
            risk_reward = reward / risk
            if risk_reward < MIN_RISK_REWARD:
                decision = "rr_below_min"
            elif risk < MIN_STOP_ATR * atr_now:
                decision = "stop_below_min"
            else:
                decision = "taken"
        found.append(
            Setup(
                direction=direction,
                d1_trend=trend,
                signal_time=signal_time,
                pivot_time=bars[confirmed].time,
                origin_time=bars[origin].time,
                pullback_level=level,
                entry=entry,
                stop=stop,
                target=target,
                risk=risk,
                reward=reward,
                risk_reward=risk_reward,
                atr=atr_now,
                decision=decision,
            )
        )
    return found


def find_exit(
    bars: Sequence[Bar],
    length: timedelta,
    *,
    direction: Direction,
    entry_time: datetime,
    stop: float,
    target: float,
) -> Exit | None:
    """Walk closed bars opening at or after `entry_time`. Stop first when a
    bar touches both levels; after `MAX_HOLD` the trade closes at the last
    close before the deadline. None while still open."""
    is_buy = direction == "buy"
    deadline = entry_time + MAX_HOLD
    last_close: float | None = None
    last_time = entry_time
    for bar in bars:
        if bar.time < entry_time:
            continue
        if bar.time >= deadline:
            return Exit("timeout", last_close if last_close is not None else bar.open, last_time)
        if (bar.low <= stop) if is_buy else (bar.high >= stop):
            return Exit("loss", stop, bar.time + length)
        if (bar.high >= target) if is_buy else (bar.low <= target):
            return Exit("win", target, bar.time + length)
        last_close, last_time = bar.close, bar.time + length
    return None

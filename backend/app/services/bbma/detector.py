"""BBMA structure detection (docs/61, ADR-148).

Pure functions over an `OHLCVSeries` - no DB, no IO, mirroring
`technical_analysis/`'s analyzer shape. Callers own persistence.

**The four tunable constants below are invented.** The source material
defines "CS Reverse" and "CS Retest" in prose only ("a candle that stops
the move", "price returns to test the highest volume"), with no body
ratio, wick tolerance or lookback anywhere across four documents
(docs/61 §7.3). They are operator-approved starting points, not
calibrated values - the same standing as ADR-028/030/035's constants.
Revisit once real BBMA outcomes exist.
"""

from app.indicators.types import OHLCVSeries
from app.indicators.volatility import atr

from .indicators import bollinger_series, ema_series, wma_series
from .types import (
    BBMAConditions,
    BBMADirection,
    BBMAResult,
    BBMASetup,
    BBMASetupKind,
)

#: How many candles after the Extreme condition to look for the reverse
#: candle. The manual describes the reverse following the Extreme
#: closely; 5 bounds the search without being so tight that a one-bar
#: pause disqualifies a valid setup.
REVERSE_SEARCH_BARS = 5

#: Minimum body-to-range ratio for a candle to count as a *rejection*
#: rather than indecision: `|close - open| >= ratio * (high - low)`.
#: Below roughly a third, the candle is a doji-ish pause and marking its
#: body as "the level the market rejected from" would be reading meaning
#: into noise.
REVERSE_MIN_BODY_RATIO = 0.30

#: How many candles after the reverse to wait for the retest. Longer than
#: the reverse window because price may wander before returning to test
#: the level - the manual explicitly has the market "try to test the
#: highest volume ... whether it can go on or stopped there".
RETEST_SEARCH_BARS = 10

#: How close a candle must come to the marked level to count as testing
#: it, as a multiple of ATR(14). Exact touches are rare, and a fixed pip
#: value cannot serve both XAUUSD and EURUSD - scaling by ATR follows the
#: magnitude-aware precedent already set by ADR-029 (round numbers) and
#: ADR-035 (equal highs/lows).
RETEST_TOLERANCE_ATR_MULTIPLE = 0.10

#: Bollinger width must grow by more than this fraction over the last
#: few bars to count as "expanding" rather than flat - the distinction
#: that decides whether a close outside the band is momentum or a
#: reversal (docs/61 §2). Also invented.
BB_EXPANSION_MIN_RATIO = 0.05
_BB_EXPANSION_LOOKBACK = 5

_BB_PERIOD = 20
_EMA_PERIOD = 50
_ATR_PERIOD = 14


def _body_ratio(open_: float, high: float, low: float, close: float) -> float:
    span = high - low
    if span <= 0:
        return 0.0
    return abs(close - open_) / span


def _is_reverse_candle(
    direction: BBMADirection,
    open_: float,
    high: float,
    low: float,
    close: float,
    band_upper: float,
    band_lower: float,
) -> bool:
    """A candle that stops the move (docs/61 §3.1).

    Two conditions, both from the source: it closes **back inside** the
    Bollinger Band (the excess is rejected), and it is the opposite
    colour to the impulse it ends. The body-ratio floor is ours.
    """
    if _body_ratio(open_, high, low, close) < REVERSE_MIN_BODY_RATIO:
        return False
    if direction is BBMADirection.SELL:
        # An up-move ending: bearish candle closing back below Top BB.
        return close < open_ and close < band_upper
    return close > open_ and close > band_lower


def _marked_level(direction: BBMADirection, open_: float, close: float) -> float:
    """The reverse candle's **body** extreme - "mark the highest body
    during the volume" (docs/61 §3.1). Body, not wick: the manual is
    explicit, and wicks would place the level where price never actually
    settled."""
    return max(open_, close) if direction is BBMADirection.SELL else min(open_, close)


def _is_retest(
    direction: BBMADirection,
    high: float,
    low: float,
    close: float,
    level: float,
    tolerance: float,
) -> bool:
    """Price returns to the marked level and is turned away again.

    Reaching the level is not enough - the candle must also **close back
    on the setup's side** of it. A close through the level is not a
    retest, it is the setup failing.
    """
    if direction is BBMADirection.SELL:
        return high >= level - tolerance and close < level
    return low <= level + tolerance and close > level


def detect(series: OHLCVSeries, *, symbol: str, timeframe: str) -> BBMAResult:
    """Walk the series once and return every completed BBMA setup.

    Order matters and is enforced: an MHV is only valid *after* an
    Extreme (docs/61 §3.3), which is why this is a single forward pass
    holding state rather than three independent scans.
    """
    warnings: list[str] = []
    closes = series.closes
    highs, lows = series.highs, series.lows
    n = len(closes)

    if n < _BB_PERIOD + REVERSE_SEARCH_BARS:
        return BBMAResult(
            symbol=symbol,
            timeframe=timeframe,
            setups=[],
            conditions=None,
            warnings=[f"Insufficient history for BBMA: {n} candles"],
        )

    bands = bollinger_series(closes, _BB_PERIOD)
    ma5h, ma10h = wma_series(highs, 5), wma_series(highs, 10)
    ma5l, ma10l = wma_series(lows, 5), wma_series(lows, 10)
    ema50 = ema_series(closes, _EMA_PERIOD)
    atr_value = atr(highs, lows, closes, _ATR_PERIOD)
    if atr_value is None or atr_value <= 0:
        warnings.append("ATR unavailable - retest tolerance falls back to zero")
    tolerance = (atr_value or 0.0) * RETEST_TOLERANCE_ATR_MULTIPLE

    setups: list[BBMASetup] = []
    #: BBMA's ordering law: MHV is only valid after an Extreme.
    last_extreme_direction: BBMADirection | None = None

    i = _BB_PERIOD
    while i < n:
        band = bands[i]
        if band is None or ma5h[i] is None or ma5l[i] is None:
            i += 1
            continue
        upper, _middle, lower = band

        # --- Law 1: an MA outside the BB is an Extreme (docs/61 §2) ---
        direction: BBMADirection | None = None
        if ma5h[i] is not None and ma5h[i] > upper:  # type: ignore[operator]
            direction = BBMADirection.SELL
        elif ma5l[i] is not None and ma5l[i] < lower:  # type: ignore[operator]
            direction = BBMADirection.BUY

        if direction is None:
            i += 1
            continue

        completed = _complete_from_extreme(
            direction=direction,
            start=i,
            series=series,
            bands=bands,
            ma5h=ma5h,
            ma10h=ma10h,
            ma5l=ma5l,
            ma10l=ma10l,
            tolerance=tolerance,
            atr_value=atr_value or 0.0,
        )
        if completed is None:
            i += 1
            continue

        setup, consumed_to = completed
        setups.append(setup)
        last_extreme_direction = direction
        i = consumed_to + 1

    conditions = _conditions_at_latest(
        series=series,
        bands=bands,
        ma5h=ma5h,
        ma10h=ma10h,
        ma5l=ma5l,
        ma10l=ma10l,
        ema50=ema50,
    )
    if last_extreme_direction is None and not setups:
        warnings.append("No BBMA Extreme found in the supplied history")

    return BBMAResult(
        symbol=symbol,
        timeframe=timeframe,
        setups=setups,
        conditions=conditions,
        warnings=warnings,
    )


def _complete_from_extreme(
    *,
    direction: BBMADirection,
    start: int,
    series: OHLCVSeries,
    bands: list[tuple[float, float, float] | None],
    ma5h: list[float | None],
    ma10h: list[float | None],
    ma5l: list[float | None],
    ma10l: list[float | None],
    tolerance: float,
    atr_value: float,
) -> tuple[BBMASetup, int] | None:
    """Extreme → CS Reverse → CS Retest, the full validation sequence
    (docs/61 §3.1). Returns the setup and the index it consumed to, or
    `None` if the sequence never completed inside its windows."""
    opens, highs, lows, closes = series.opens, series.highs, series.lows, series.closes
    n = len(closes)

    reverse_index: int | None = None
    for j in range(start, min(start + REVERSE_SEARCH_BARS + 1, n)):
        band = bands[j]
        if band is None:
            continue
        upper, _mid, lower = band
        if _is_reverse_candle(direction, opens[j], highs[j], lows[j], closes[j], upper, lower):
            reverse_index = j
            break
    if reverse_index is None:
        return None

    level = _marked_level(direction, opens[reverse_index], closes[reverse_index])

    for k in range(reverse_index + 1, min(reverse_index + RETEST_SEARCH_BARS + 1, n)):
        if not _is_retest(direction, highs[k], lows[k], closes[k], level, tolerance):
            continue

        # Entry at the MA5/10 band, per BBMA's entry law - never at the
        # marked level itself (docs/61 §2).
        if direction is BBMADirection.SELL:
            band_values = [v for v in (ma5h[k], ma10h[k]) if v is not None]
        else:
            band_values = [v for v in (ma5l[k], ma10l[k]) if v is not None]
        if not band_values:
            continue
        entry = sum(band_values) / len(band_values)

        # Invalidation sits beyond the extreme wick of the move, not
        # beyond the marked body - a new extreme is what kills the setup.
        window_highs = highs[start : k + 1]
        window_lows = lows[start : k + 1]
        if direction is BBMADirection.SELL:
            stop = max(window_highs)
            band = bands[k]
            target = band[1] if band is not None else entry - (stop - entry) * 2
        else:
            stop = min(window_lows)
            band = bands[k]
            target = band[1] if band is not None else entry + (entry - stop) * 2

        return (
            BBMASetup(
                kind=BBMASetupKind.EXTREME,
                direction=direction,
                entry_index=k,
                marked_level=level,
                entry_price=entry,
                stop_loss=stop,
                # Extreme's TP is mandatory at MA5/10, at most Mid BB
                # (docs/61 §6.2) - Mid BB is used as the conservative
                # single value.
                take_profit=target,
                notes=[
                    f"Extreme {direction.value} at bar {start}",
                    f"CS Reverse at bar {reverse_index} (body level {level:.5f})",
                    f"CS Retest at bar {k}",
                ],
            ),
            k,
        )
    return None


def _conditions_at_latest(
    *,
    series: OHLCVSeries,
    bands: list[tuple[float, float, float] | None],
    ma5h: list[float | None],
    ma10h: list[float | None],
    ma5l: list[float | None],
    ma10l: list[float | None],
    ema50: list[float | None],
) -> BBMAConditions | None:
    i = len(series.closes) - 1
    band = bands[i]
    if band is None:
        return None
    upper, middle, lower = band
    close, open_ = series.closes[i], series.opens[i]

    csm = close > upper or close < lower
    csak = (close > middle >= open_) or (close < middle <= open_)

    highs_band = [v for v in (ma5h[i], ma10h[i]) if v is not None]
    lows_band = [v for v in (ma5l[i], ma10l[i]) if v is not None]
    csk = bool(
        (highs_band and close > max(highs_band)) or (lows_band and close < min(lows_band))
    )

    ema = ema50[i]
    trend_major: BBMADirection | None = None
    if ema is not None:
        trend_major = BBMADirection.BUY if close > ema else BBMADirection.SELL

    # ZZL: every MA one side of Mid BB, and Mid BB the same side of EMA50
    # (docs/61 §3.8).
    zzl = False
    all_mas = [v for v in (ma5h[i], ma10h[i], ma5l[i], ma10l[i]) if v is not None]
    if ema is not None and len(all_mas) == 4:
        zzl = (all(v > middle for v in all_mas) and middle > ema) or (
            all(v < middle for v in all_mas) and middle < ema
        )

    bb_expanding = False
    past = bands[i - _BB_EXPANSION_LOOKBACK] if i >= _BB_EXPANSION_LOOKBACK else None
    if past is not None:
        now_width, past_width = upper - lower, past[0] - past[2]
        if past_width > 0:
            bb_expanding = (now_width - past_width) / past_width > BB_EXPANSION_MIN_RATIO

    return BBMAConditions(
        csm=csm,
        csak=csak,
        csk=csk,
        zzl=zzl,
        trend_major=trend_major,
        bb_expanding=bb_expanding,
    )


__all__ = ["detect"]

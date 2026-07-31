"""docs/16 §13 Volatility Regime. Technical Analysis only exposes the
*latest* ATR value - classifying a regime needs a trend in volatility,
so this computes a full ATR series via the same shared
`true_ranges`/`wilder_smoothed_series` utilities Technical Analysis's
own `atr()` uses (docs/44 §7), not a duplicated calculation.

Bands are relative (recent vs. baseline average), a magnitude-aware
choice consistent with ADR-029/ADR-035's precedent - a fixed absolute
ATR threshold wouldn't generalize across asset price scales.
"""

from collections.abc import Sequence

from app.indicators._utils import true_ranges, wilder_smoothed_series
from app.models.price_candle import PriceCandle
from app.services.market_regime.types import VolatilityRegimeEvidence, VolatilityRegimeState

_ATR_PERIOD = 14
_RECENT_WINDOW = 14

_VERY_LOW_MAX = 0.5
_LOW_MAX = 0.8
_NORMAL_MAX = 1.25
_HIGH_MAX = 2.0


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def analyze(candles: Sequence[PriceCandle]) -> VolatilityRegimeEvidence:
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]
    closes = [float(c.close) for c in candles]

    ranges = true_ranges(highs, lows, closes)
    atr_series = wilder_smoothed_series(ranges, _ATR_PERIOD)

    if not atr_series:
        return VolatilityRegimeEvidence(
            state=VolatilityRegimeState.NORMAL, recent_atr_average=None, baseline_atr_average=None
        )

    baseline_atr_average = _mean(atr_series)
    recent_window = min(_RECENT_WINDOW, len(atr_series))
    recent_atr_average = _mean(atr_series[-recent_window:])

    ratio = recent_atr_average / baseline_atr_average if baseline_atr_average > 0 else 1.0

    if ratio < _VERY_LOW_MAX:
        state = VolatilityRegimeState.VERY_LOW
    elif ratio < _LOW_MAX:
        state = VolatilityRegimeState.LOW
    elif ratio <= _NORMAL_MAX:
        state = VolatilityRegimeState.NORMAL
    elif ratio <= _HIGH_MAX:
        state = VolatilityRegimeState.HIGH
    else:
        state = VolatilityRegimeState.EXTREME

    return VolatilityRegimeEvidence(
        state=state,
        recent_atr_average=recent_atr_average,
        baseline_atr_average=baseline_atr_average,
    )

"""Shared numeric helpers used by multiple indicator modules.

Not registered in the indicator registry themselves - these are building
blocks (EMA/SMA series, Wilder smoothing), not indicators exposed to
docs/08 §5's list.
"""

import math


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_full(values: list[float], period: int) -> list[float | None]:
    """EMA at every index (`None` before enough data), seeded with an SMA."""
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    multiplier = 2 / (period + 1)
    prev = sum(values[:period]) / period
    result[period - 1] = prev
    for i in range(period, len(values)):
        prev = (values[i] - prev) * multiplier + prev
        result[i] = prev
    return result


def ema(values: list[float], period: int) -> float | None:
    series = ema_full(values, period)
    return series[-1] if series else None


def wilder_smoothed_series(values: list[float], period: int) -> list[float] | None:
    """Wilder's smoothing (used by RSI, ATR, ADX), seeded with a simple
    average of the first `period` values. Returns the full smoothed
    series (length `len(values) - period + 1`), oldest first."""
    if len(values) < period:
        return None

    smoothed = [sum(values[:period]) / period]
    for value in values[period:]:
        smoothed.append((smoothed[-1] * (period - 1) + value) / period)
    return smoothed


def true_ranges(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    """True Range at each index from 1 onward (index 0 has no previous close)."""
    ranges: list[float] = []
    for i in range(1, len(highs)):
        prev_close = closes[i - 1]
        ranges.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - prev_close),
                abs(lows[i] - prev_close),
            )
        )
    return ranges


def population_stdev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)

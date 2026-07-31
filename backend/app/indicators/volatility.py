"""Volatility indicators, per docs/08_TECHNICAL_ANALYSIS_ENGINE.md §5 "Volatility"."""

from app.indicators._utils import population_stdev, sma, true_ranges, wilder_smoothed_series
from app.indicators.registry import registry
from app.indicators.types import IndicatorOutput, OHLCVSeries


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> float | None:
    ranges = true_ranges(highs, lows, closes)
    smoothed = wilder_smoothed_series(ranges, period)
    return smoothed[-1] if smoothed else None


def bollinger_bands(
    closes: list[float], period: int = 20, std_dev_multiplier: float = 2.0
) -> tuple[float, float, float] | None:
    """Returns (upper, middle, lower)."""
    middle = sma(closes, period)
    if middle is None:
        return None

    std = population_stdev(closes[-period:])
    return middle + std_dev_multiplier * std, middle, middle - std_dev_multiplier * std


def standard_deviation(closes: list[float], period: int = 20) -> float | None:
    if len(closes) < period:
        return None
    return population_stdev(closes[-period:])


def _atr_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = atr(series.highs, series.lows, series.closes, 14)
    return None if value is None else IndicatorOutput(value=value)


def _bollinger_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    result = bollinger_bands(series.closes, 20, 2.0)
    if result is None:
        return None
    upper, middle, lower = result
    return IndicatorOutput(value=middle, metadata={"upper": upper, "lower": lower})


def _stddev_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = standard_deviation(series.closes, 20)
    return None if value is None else IndicatorOutput(value=value)


registry.register("atr_14", "volatility", _atr_indicator)
registry.register("bollinger_bands_20", "volatility", _bollinger_indicator)
registry.register("stddev_20", "volatility", _stddev_indicator)

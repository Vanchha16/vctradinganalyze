"""Momentum indicators, per docs/08_TECHNICAL_ANALYSIS_ENGINE.md §5 "Momentum"."""

from app.indicators._utils import ema_full, wilder_smoothed_series
from app.indicators.registry import registry
from app.indicators.types import IndicatorOutput, OHLCVSeries


def _price_deltas(values: list[float]) -> tuple[list[float], list[float]]:
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    return gains, losses


def rsi_series(values: list[float], period: int) -> list[float] | None:
    """RSI at every index from `period` onward (Wilder smoothing)."""
    gains, losses = _price_deltas(values)
    smoothed_gains = wilder_smoothed_series(gains, period)
    smoothed_losses = wilder_smoothed_series(losses, period)
    if smoothed_gains is None or smoothed_losses is None:
        return None

    result = []
    for gain, loss in zip(smoothed_gains, smoothed_losses, strict=True):
        if loss == 0:
            result.append(100.0)
        else:
            rs = gain / loss
            result.append(100 - (100 / (1 + rs)))
    return result


def rsi(values: list[float], period: int = 14) -> float | None:
    series = rsi_series(values, period)
    return series[-1] if series else None


def macd(
    values: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float, float] | None:
    """Returns (macd_line, signal_line, histogram)."""
    fast_full = ema_full(values, fast)
    slow_full = ema_full(values, slow)
    macd_line = [
        f - s if f is not None and s is not None else None
        for f, s in zip(fast_full, slow_full, strict=True)
    ]
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal:
        return None

    signal_full = ema_full(valid_macd, signal)
    signal_value = signal_full[-1]
    if signal_value is None:
        return None

    macd_value = valid_macd[-1]
    return macd_value, signal_value, macd_value - signal_value


def stochastic_rsi(values: list[float], period: int = 14) -> float | None:
    series = rsi_series(values, period)
    if series is None or len(series) < period:
        return None

    window = series[-period:]
    lowest, highest = min(window), max(window)
    if highest == lowest:
        return 0.0
    return (series[-1] - lowest) / (highest - lowest) * 100


def cci(
    highs: list[float], lows: list[float], closes: list[float], period: int = 20
) -> float | None:
    if len(closes) < period:
        return None

    typical_prices = [(h + low + c) / 3 for h, low, c in zip(highs, lows, closes, strict=True)]
    window = typical_prices[-period:]
    mean_price = sum(window) / period
    mean_deviation = sum(abs(p - mean_price) for p in window) / period
    if mean_deviation == 0:
        return 0.0
    return (typical_prices[-1] - mean_price) / (0.015 * mean_deviation)


def momentum(values: list[float], period: int = 10) -> float | None:
    if len(values) < period + 1:
        return None
    return values[-1] - values[-1 - period]


def _rsi_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = rsi(series.closes, 14)
    return None if value is None else IndicatorOutput(value=value)


def _macd_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    result = macd(series.closes)
    if result is None:
        return None
    macd_value, signal_value, histogram = result
    return IndicatorOutput(
        value=macd_value, metadata={"signal": signal_value, "histogram": histogram}
    )


def _stoch_rsi_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = stochastic_rsi(series.closes, 14)
    return None if value is None else IndicatorOutput(value=value)


def _cci_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = cci(series.highs, series.lows, series.closes, 20)
    return None if value is None else IndicatorOutput(value=value)


def _momentum_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = momentum(series.closes, 10)
    return None if value is None else IndicatorOutput(value=value)


registry.register("rsi_14", "momentum", _rsi_indicator)
registry.register("macd", "momentum", _macd_indicator)
registry.register("stoch_rsi_14", "momentum", _stoch_rsi_indicator)
registry.register("cci_20", "momentum", _cci_indicator)
registry.register("momentum_10", "momentum", _momentum_indicator)

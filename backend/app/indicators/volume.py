"""Volume indicators, per docs/08_TECHNICAL_ANALYSIS_ENGINE.md §5 "Volume"."""

from app.indicators._utils import sma
from app.indicators.registry import registry
from app.indicators.types import IndicatorOutput, OHLCVSeries


def vwap(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float | None]
) -> float | None:
    """Volume-weighted average price over the entire provided series.

    Simplified from the traditional intraday-session VWAP (which resets
    daily) to a full-window calculation - Phase 3A has no session-boundary
    concept yet. Revisit if session-based VWAP is needed later.
    """
    total_volume = 0.0
    total_value = 0.0
    for h, low, c, v in zip(highs, lows, closes, volumes, strict=True):
        volume = v or 0.0
        typical_price = (h + low + c) / 3
        total_value += typical_price * volume
        total_volume += volume
    if total_volume == 0:
        return None
    return total_value / total_volume


def obv(closes: list[float], volumes: list[float | None]) -> float | None:
    if len(closes) < 2:
        return None

    running = 0.0
    for i in range(1, len(closes)):
        volume = volumes[i] or 0.0
        if closes[i] > closes[i - 1]:
            running += volume
        elif closes[i] < closes[i - 1]:
            running -= volume
    return running


def volume_sma(volumes: list[float | None], period: int = 20) -> float | None:
    values = [v for v in volumes if v is not None]
    return sma(values, period)


def relative_volume(volumes: list[float | None], period: int = 20) -> float | None:
    if not volumes or volumes[-1] is None:
        return None
    average = volume_sma(volumes[:-1], period)
    if not average:
        return None
    return volumes[-1] / average


def _vwap_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = vwap(series.highs, series.lows, series.closes, series.volumes)
    return None if value is None else IndicatorOutput(value=value)


def _obv_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = obv(series.closes, series.volumes)
    return None if value is None else IndicatorOutput(value=value)


def _volume_sma_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = volume_sma(series.volumes, 20)
    return None if value is None else IndicatorOutput(value=value)


def _relative_volume_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    value = relative_volume(series.volumes, 20)
    return None if value is None else IndicatorOutput(value=value)


registry.register("vwap", "volume", _vwap_indicator)
registry.register("obv", "volume", _obv_indicator)
registry.register("volume_sma_20", "volume", _volume_sma_indicator)
registry.register("relative_volume_20", "volume", _relative_volume_indicator)

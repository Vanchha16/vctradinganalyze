"""Trend indicators, per docs/08_TECHNICAL_ANALYSIS_ENGINE.md §5 "Trend"."""

from app.indicators._utils import ema, sma
from app.indicators.registry import registry
from app.indicators.types import IndicatorOutput, OHLCVSeries


def _ema_indicator(period: int) -> None:
    def _fn(series: OHLCVSeries) -> IndicatorOutput | None:
        value = ema(series.closes, period)
        return None if value is None else IndicatorOutput(value=value)

    registry.register(f"ema_{period}", "trend", _fn)


def _sma_indicator(period: int) -> None:
    def _fn(series: OHLCVSeries) -> IndicatorOutput | None:
        value = sma(series.closes, period)
        return None if value is None else IndicatorOutput(value=value)

    registry.register(f"sma_{period}", "trend", _fn)


for _period in (20, 50, 100, 200):
    _ema_indicator(_period)
_sma_indicator(200)

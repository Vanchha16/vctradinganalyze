"""Trend-strength indicators, per docs/08_TECHNICAL_ANALYSIS_ENGINE.md §5 "Trend Strength"."""

from app.indicators._utils import true_ranges, wilder_smoothed_series
from app.indicators.registry import registry
from app.indicators.types import IndicatorOutput, OHLCVSeries


def adx(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> tuple[float, float, float] | None:
    """Returns (adx, di_plus, di_minus), per Wilder's original formulation."""
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for i in range(1, len(highs)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0.0)

    tr = true_ranges(highs, lows, closes)
    smoothed_tr = wilder_smoothed_series(tr, period)
    smoothed_plus_dm = wilder_smoothed_series(plus_dm, period)
    smoothed_minus_dm = wilder_smoothed_series(minus_dm, period)
    if smoothed_tr is None or smoothed_plus_dm is None or smoothed_minus_dm is None:
        return None

    plus_di_series: list[float] = []
    minus_di_series: list[float] = []
    dx_series: list[float] = []
    for tr_v, pdm_v, mdm_v in zip(smoothed_tr, smoothed_plus_dm, smoothed_minus_dm, strict=True):
        plus_di = 0.0 if tr_v == 0 else 100 * pdm_v / tr_v
        minus_di = 0.0 if tr_v == 0 else 100 * mdm_v / tr_v
        plus_di_series.append(plus_di)
        minus_di_series.append(minus_di)
        denom = plus_di + minus_di
        dx_series.append(0.0 if denom == 0 else 100 * abs(plus_di - minus_di) / denom)

    adx_series = wilder_smoothed_series(dx_series, period)
    if not adx_series:
        return None
    return adx_series[-1], plus_di_series[-1], minus_di_series[-1]


def _adx_indicator(series: OHLCVSeries) -> IndicatorOutput | None:
    result = adx(series.highs, series.lows, series.closes, 14)
    if result is None:
        return None
    adx_value, di_plus, di_minus = result
    return IndicatorOutput(value=adx_value, metadata={"di_plus": di_plus, "di_minus": di_minus})


registry.register("adx_14", "trend_strength", _adx_indicator)

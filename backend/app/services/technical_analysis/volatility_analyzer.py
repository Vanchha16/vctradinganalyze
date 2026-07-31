"""docs/08 §5 Volatility: ATR, Bollinger Bands, Standard Deviation."""

from app.indicators.types import IndicatorOutput
from app.services.technical_analysis.types import VolatilityEvidence, VolatilityState

#: Band width relative to the middle band, below which conditions are
#: classified as a volatility squeeze (docs/42 §9 heuristic).
_SQUEEZE_BAND_WIDTH_RATIO = 0.02


def analyze(indicators: dict[str, IndicatorOutput], current_price: float) -> VolatilityEvidence:
    atr_output = indicators.get("atr_14")
    bollinger_output = indicators.get("bollinger_bands_20")
    stddev_output = indicators.get("stddev_20")

    atr = atr_output.value if atr_output is not None else None
    stddev = stddev_output.value if stddev_output is not None else None

    upper: float | None = None
    lower: float | None = None
    state = VolatilityState.UNAVAILABLE

    if bollinger_output is not None and bollinger_output.metadata is not None:
        upper = bollinger_output.metadata.get("upper")
        lower = bollinger_output.metadata.get("lower")
        middle = bollinger_output.value

        if upper is not None and lower is not None and middle:
            band_width_ratio = (upper - lower) / middle
            if band_width_ratio < _SQUEEZE_BAND_WIDTH_RATIO:
                state = VolatilityState.SQUEEZE
            elif current_price >= upper:
                state = VolatilityState.NEAR_UPPER_BAND
            elif current_price <= lower:
                state = VolatilityState.NEAR_LOWER_BAND
            else:
                state = VolatilityState.STABLE

    return VolatilityEvidence(
        atr=atr, bollinger_upper=upper, bollinger_lower=lower, stddev=stddev, state=state
    )

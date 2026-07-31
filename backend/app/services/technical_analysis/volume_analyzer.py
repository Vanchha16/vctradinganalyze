"""docs/08 §5 Volume: VWAP, OBV, Relative Volume.

Not in your example analyzer tree, but added because docs/08 §5 treats
Volume as its own first-class indicator category (distinct from
Momentum/Volatility), and §9's scoring example includes "VWAP Above
Price" as its own factor.
"""

from app.indicators.types import IndicatorOutput
from app.services.technical_analysis.types import VolumeEvidence, VolumeState

_RELATIVE_VOLUME_ABOVE_AVERAGE = 1.0


def analyze(indicators: dict[str, IndicatorOutput], current_price: float) -> VolumeEvidence:
    vwap_output = indicators.get("vwap")
    obv_output = indicators.get("obv")
    relative_volume_output = indicators.get("relative_volume_20")

    price_above_vwap = None if vwap_output is None else current_price > vwap_output.value
    obv = obv_output.value if obv_output is not None else None
    relative_volume = relative_volume_output.value if relative_volume_output is not None else None

    if relative_volume is None:
        state = VolumeState.UNAVAILABLE
    elif relative_volume >= _RELATIVE_VOLUME_ABOVE_AVERAGE:
        state = VolumeState.ABOVE_AVERAGE
    else:
        state = VolumeState.BELOW_AVERAGE

    return VolumeEvidence(
        price_above_vwap=price_above_vwap,
        obv=obv,
        relative_volume=relative_volume,
        relative_volume_state=state,
    )

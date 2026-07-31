"""docs/08 §7 Trend Detection - the final trend/strength verdict, combining
moving-average alignment with ADX-based strength (docs/42 §9)."""

from app.indicators.types import IndicatorOutput
from app.services.technical_analysis import moving_average_analyzer
from app.services.technical_analysis.types import TrendDirection, TrendEvidence, TrendStrengthLevel

_VERY_STRONG_ADX = 40.0
_STRONG_ADX = 25.0
_MODERATE_ADX = 20.0


def analyze(indicators: dict[str, IndicatorOutput], current_price: float) -> TrendEvidence:
    ma_evidence = moving_average_analyzer.analyze(indicators, current_price)

    adx_output = indicators.get("adx_14")
    adx = adx_output.value if adx_output is not None else None
    di_plus = (
        adx_output.metadata.get("di_plus")
        if adx_output is not None and adx_output.metadata
        else None
    )
    di_minus = (
        adx_output.metadata.get("di_minus")
        if adx_output is not None and adx_output.metadata
        else None
    )

    if ma_evidence.bullish_alignment:
        direction = TrendDirection.BULLISH
    elif ma_evidence.bearish_alignment:
        direction = TrendDirection.BEARISH
    else:
        direction = TrendDirection.SIDEWAYS

    if adx is None:
        strength = TrendStrengthLevel.WEAK
    elif adx >= _VERY_STRONG_ADX:
        strength = TrendStrengthLevel.VERY_STRONG
    elif adx >= _STRONG_ADX:
        strength = TrendStrengthLevel.STRONG
    elif adx >= _MODERATE_ADX:
        strength = TrendStrengthLevel.MODERATE
    else:
        strength = TrendStrengthLevel.WEAK

    return TrendEvidence(
        direction=direction,
        strength=strength,
        adx=adx,
        di_plus=di_plus,
        di_minus=di_minus,
        moving_average=ma_evidence,
    )

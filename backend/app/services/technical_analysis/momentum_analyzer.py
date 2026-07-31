"""docs/08 §5 Momentum: MACD + raw Momentum indicator."""

from app.indicators.types import IndicatorOutput
from app.services.technical_analysis.types import MomentumEvidence


def analyze(indicators: dict[str, IndicatorOutput]) -> MomentumEvidence:
    macd_output = indicators.get("macd")
    momentum_output = indicators.get("momentum_10")

    macd = macd_output.value if macd_output is not None else None
    macd_signal = (
        macd_output.metadata.get("signal")
        if macd_output is not None and macd_output.metadata
        else None
    )
    macd_histogram = (
        macd_output.metadata.get("histogram")
        if macd_output is not None and macd_output.metadata
        else None
    )
    macd_bullish = None if macd is None or macd_signal is None else macd > macd_signal

    momentum = momentum_output.value if momentum_output is not None else None
    momentum_positive = None if momentum is None else momentum > 0

    return MomentumEvidence(
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        macd_bullish=macd_bullish,
        momentum=momentum,
        momentum_positive=momentum_positive,
    )

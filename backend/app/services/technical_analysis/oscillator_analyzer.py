"""docs/08 §5 Momentum oscillators: RSI, Stochastic RSI, CCI - bounded
indicators with overbought/oversold zones, distinct from MACD/Momentum
(unbounded, trend-following) which MomentumAnalyzer owns."""

from app.indicators.types import IndicatorOutput
from app.services.technical_analysis.types import OscillatorEvidence, OscillatorState

_RSI_OVERBOUGHT = 70.0
_RSI_OVERSOLD = 30.0
_STOCH_RSI_OVERBOUGHT = 80.0
_STOCH_RSI_OVERSOLD = 20.0
_CCI_OVERBOUGHT = 100.0
_CCI_OVERSOLD = -100.0


def _classify(value: float | None, overbought: float, oversold: float) -> OscillatorState:
    if value is None:
        return OscillatorState.UNAVAILABLE
    if value >= overbought:
        return OscillatorState.OVERBOUGHT
    if value <= oversold:
        return OscillatorState.OVERSOLD
    return OscillatorState.HEALTHY


def analyze(indicators: dict[str, IndicatorOutput]) -> OscillatorEvidence:
    rsi_output = indicators.get("rsi_14")
    stoch_output = indicators.get("stoch_rsi_14")
    cci_output = indicators.get("cci_20")

    rsi = rsi_output.value if rsi_output is not None else None
    stoch_rsi = stoch_output.value if stoch_output is not None else None
    cci = cci_output.value if cci_output is not None else None

    return OscillatorEvidence(
        rsi=rsi,
        rsi_state=_classify(rsi, _RSI_OVERBOUGHT, _RSI_OVERSOLD),
        stoch_rsi=stoch_rsi,
        stoch_rsi_state=_classify(stoch_rsi, _STOCH_RSI_OVERBOUGHT, _STOCH_RSI_OVERSOLD),
        cci=cci,
        cci_state=_classify(cci, _CCI_OVERBOUGHT, _CCI_OVERSOLD),
    )

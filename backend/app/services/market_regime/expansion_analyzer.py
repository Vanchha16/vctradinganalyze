"""Supporting expansion/contraction evidence (not a top-level docs/16
§3 regime value - see docs/44 §2). Reuses `VolatilityRegimeAnalyzer`'s
already-computed recent/baseline ATR averages rather than recomputing
the ATR series a second time within the same engine execution.
"""

from app.services.market_regime.types import (
    ExpansionEvidence,
    ExpansionState,
    VolatilityRegimeEvidence,
)

_EXPANSION_MIN_RATIO = 1.15
_CONTRACTION_MAX_RATIO = 0.85


def analyze(volatility: VolatilityRegimeEvidence) -> ExpansionEvidence:
    if volatility.recent_atr_average is None or not volatility.baseline_atr_average:
        return ExpansionEvidence(state=ExpansionState.STABLE, ratio=None)

    ratio = volatility.recent_atr_average / volatility.baseline_atr_average

    if ratio > _EXPANSION_MIN_RATIO:
        state = ExpansionState.EXPANSION
    elif ratio < _CONTRACTION_MAX_RATIO:
        state = ExpansionState.CONTRACTION
    else:
        state = ExpansionState.STABLE

    return ExpansionEvidence(state=state, ratio=ratio)

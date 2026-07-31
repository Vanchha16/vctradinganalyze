"""RegimeConfidenceEngine: produces `RegimeConfidenceBreakdown`, mirroring
Technical Analysis's `ScoreBreakdown`/SMC's `SMCScoreBreakdown` explainable
pattern (ADR-028/ADR-036) - but `confidence` measures how reliable *this
classification* is, never combined with `technical_score`/`smc_score`
(ADR-042). Deliberately not named "*Score*" - this engine classifies
market conditions, it does not produce another evidence-strength score.
"""

from app.services.market_regime.regime_classifier import (
    ALIGNMENT_BONUS,
    TREND_STRENGTH_BASE,
    ClassificationOutcome,
)
from app.services.market_regime.types import (
    RegimeConfidenceBreakdown,
    RegimeConflictReport,
    TrendRegimeEvidence,
    VolatilityRegimeEvidence,
    VolatilityRegimeState,
)

_TREND_CLARITY_MAX = 35.0
_VOLATILITY_CLARITY_NOTABLE = 25.0
_VOLATILITY_CLARITY_BASELINE = 15.0
_STRUCTURAL_CONFIRMATION_MAX = 40.0
_CONFLICT_PENALTY_PER_CONFLICT = 5.0

_TREND_STRENGTH_SCALE = 95.0  # matches regime_classifier.TREND_STRENGTH_BASE's max (VERY_STRONG)


def score(
    trend_regime: TrendRegimeEvidence,
    volatility: VolatilityRegimeEvidence,
    outcome: ClassificationOutcome,
    conflicts: RegimeConflictReport,
) -> RegimeConfidenceBreakdown:
    trend_base = TREND_STRENGTH_BASE.get(trend_regime.strength, 0.0)
    trend_clarity = min(
        _TREND_CLARITY_MAX,
        (trend_base / _TREND_STRENGTH_SCALE) * _TREND_CLARITY_MAX
        + (ALIGNMENT_BONUS / 10.0 if trend_regime.aligned else 0.0),
    )

    volatility_clarity = (
        _VOLATILITY_CLARITY_NOTABLE
        if volatility.state != VolatilityRegimeState.NORMAL
        else _VOLATILITY_CLARITY_BASELINE
    )

    structural_confirmation = (
        (outcome.winner.confidence / 100.0) * _STRUCTURAL_CONFIRMATION_MAX
        if outcome.winner is not None
        else 0.0
    )

    conflict_penalty = -(_CONFLICT_PENALTY_PER_CONFLICT * len(conflicts.conflicts))

    return RegimeConfidenceBreakdown(
        trend_clarity=trend_clarity,
        volatility_clarity=volatility_clarity,
        structural_confirmation=structural_confirmation,
        stability_penalty=outcome.stability_penalty,
        conflict_penalty=conflict_penalty,
    )

"""Pullback requirements checklist (docs/17 §10, docs/49 §5). Strong
trend, temporary retracement, support holds, momentum recovery - all
already-computed evidence."""

from app.services.market_regime.types import PullbackDepth
from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle
from app.services.technical_analysis.types import TrendStrengthLevel

_STRONG_TREND = frozenset({TrendStrengthLevel.STRONG, TrendStrengthLevel.VERY_STRONG})


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    if evidence.market_regime is None or evidence.technical is None:
        return RequirementsResult(met_count=0, total_count=4)

    strong_trend = evidence.technical.trend_evidence.strength in _STRONG_TREND

    pullback = evidence.market_regime.pullback_reversal
    temporary_retracement = pullback.pullback_depth is PullbackDepth.HEALTHY

    support_holds = evidence.technical.support is not None

    momentum_recovery = (
        pullback.reversal_confidence is not None and pullback.reversal_confidence > 0
    )

    met_count = sum([strong_trend, temporary_retracement, support_holds, momentum_recovery])
    return RequirementsResult(met_count=met_count, total_count=4)

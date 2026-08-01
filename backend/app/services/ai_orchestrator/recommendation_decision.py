"""Deterministic recommendation decision tree (docs/50 §6, ADR-078). The
LLM never decides the recommendation - it receives this already-decided
value and narrates why. Directly implements docs/13 §6's prose rules and
§9's worked conflict example as a concrete, testable algorithm."""

from dataclasses import dataclass

from app.models.enums import Recommendation
from app.services.analysis_confidence.types import ConfidenceLevel, ConflictSeverity
from app.services.risk_management.types import TradeDirection

from .types import AnalysisContext

_LOW_CONFIDENCE_LEVELS = frozenset({ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW})


@dataclass(frozen=True, slots=True)
class RecommendationDecision:
    recommendation: Recommendation
    reasons: list[str]


def decide(context: AnalysisContext) -> RecommendationDecision:
    if context.candidate_setup is None:
        return RecommendationDecision(
            recommendation=Recommendation.WAIT,
            reasons=["No viable strategy for current conditions."],
        )

    if context.risk is not None and not context.risk.approved:
        reasons = list(context.risk.rejected_reasons) or ["Risk Engine rejected this setup."]
        return RecommendationDecision(recommendation=Recommendation.WAIT, reasons=reasons)

    if context.confidence.confidence_level in _LOW_CONFIDENCE_LEVELS:
        return RecommendationDecision(
            recommendation=Recommendation.WAIT,
            reasons=["Confidence too low for a reliable recommendation."],
        )

    if context.confidence.conflict_severity is ConflictSeverity.HIGH:
        return RecommendationDecision(
            recommendation=Recommendation.WAIT,
            reasons=["Conflicting evidence across engines."],
        )

    recommendation = (
        Recommendation.BUY
        if context.candidate_setup.direction is TradeDirection.LONG
        else Recommendation.SELL
    )
    return RecommendationDecision(recommendation=recommendation, reasons=[])

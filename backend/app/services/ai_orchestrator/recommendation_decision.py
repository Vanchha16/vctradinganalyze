"""Deterministic recommendation decision tree (docs/50 §6, ADR-078). The
LLM never decides the recommendation - it receives this already-decided
value and narrates why. Directly implements docs/13 §6's prose rules and
§9's worked conflict example as a concrete, testable algorithm.

ADR-166 adds one rule: a setup whose higher timeframes trend against it is
held back as WAIT. Still deterministic - a trend direction compared with a
trade direction - so the AI still decides nothing."""

from dataclasses import dataclass

from app.models.enums import Recommendation
from app.services.analysis_confidence.types import ConfidenceLevel, ConflictSeverity
from app.services.risk_management.types import TradeDirection
from app.services.technical_analysis.types import TrendDirection

from .types import AnalysisContext, CandidateSetup

_LOW_CONFIDENCE_LEVELS = frozenset({ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW})


@dataclass(frozen=True, slots=True)
class RecommendationDecision:
    recommendation: Recommendation
    reasons: list[str]


def decide(context: AnalysisContext) -> RecommendationDecision:
    setup = context.candidate_setup
    if setup is None:
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

    opposing = _opposing_higher_timeframes(setup, context)
    if opposing:
        return RecommendationDecision(
            recommendation=Recommendation.WAIT,
            reasons=[f"Higher timeframe trend runs against the setup ({', '.join(opposing)})."],
        )

    recommendation = (
        Recommendation.BUY if setup.direction is TradeDirection.LONG else Recommendation.SELL
    )
    return RecommendationDecision(recommendation=recommendation, reasons=[])


def _opposing_higher_timeframes(setup: CandidateSetup, context: AnalysisContext) -> list[str]:
    """ADR-166. Only a trend in the *opposite* direction blocks. Sideways is
    no objection, and a timeframe with no data is not evidence either way -
    blocking on missing data would silence every signal while D1's history
    is still thin."""
    opposite = (
        TrendDirection.BEARISH if setup.direction is TradeDirection.LONG else TrendDirection.BULLISH
    )
    return [
        view.timeframe.value.upper()
        for view in context.higher_timeframes
        if view.technical is not None and view.technical.trend is opposite
    ]

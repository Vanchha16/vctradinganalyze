"""docs/16 §3/§15 regime classification (ADR-039). Per Phase 4C
approval: evaluate confidence for *every* candidate regime first, filter
to those clearing `MIN_CONFIDENCE_TO_QUALIFY`, and only then apply the
documented precedence order among the survivors - reducing false
positives from a naive "first matching condition wins" approach.

The margin check (`MIN_MARGIN`) is the anti-oscillation/stability
safeguard from ADR-044: a winning candidate that only narrowly beats the
next-best qualifying candidate is reported with a confidence penalty and
a warning, rather than committing to a sharp classification a small
input perturbation could easily flip.
"""

from dataclasses import dataclass, field

from app.services.market_regime.types import (
    AccumulationDistributionEvidence,
    BreakoutDirection,
    BreakoutEvidence,
    MarketRegimeState,
    PullbackDepth,
    PullbackReversalEvidence,
    RangeEvidence,
    RegimeCandidate,
    TrendRegimeEvidence,
    VolatilityRegimeEvidence,
    VolatilityRegimeState,
)
from app.services.technical_analysis.types import TrendDirection, TrendStrengthLevel

MIN_CONFIDENCE_TO_QUALIFY = 60.0
MIN_MARGIN = 10.0

_PRECEDENCE: dict[MarketRegimeState, int] = {
    MarketRegimeState.REVERSAL: 1,
    MarketRegimeState.BREAKOUT: 2,
    MarketRegimeState.DISTRIBUTION: 3,
    MarketRegimeState.ACCUMULATION: 3,
    MarketRegimeState.TRENDING_BULLISH: 4,
    MarketRegimeState.TRENDING_BEARISH: 4,
    MarketRegimeState.PULLBACK: 5,
    MarketRegimeState.RANGING: 6,
    MarketRegimeState.HIGH_VOLATILITY: 7,
    MarketRegimeState.LOW_VOLATILITY: 7,
}

TREND_STRENGTH_BASE: dict[TrendStrengthLevel, float] = {
    TrendStrengthLevel.WEAK: 40.0,
    TrendStrengthLevel.MODERATE: 60.0,
    TrendStrengthLevel.STRONG: 80.0,
    TrendStrengthLevel.VERY_STRONG: 95.0,
}
ALIGNMENT_BONUS = 10.0

_PULLBACK_CONFIDENCE: dict[PullbackDepth, float] = {
    PullbackDepth.HEALTHY: 70.0,
    PullbackDepth.DEEP: 60.0,
    PullbackDepth.POTENTIAL_REVERSAL: 50.0,
}
_RANGE_STRENGTH_CONFIDENCE = {"weak": 55.0, "moderate": 70.0, "strong": 85.0}
_HIGH_VOLATILITY_CONFIDENCE = {
    VolatilityRegimeState.HIGH: 65.0,
    VolatilityRegimeState.EXTREME: 85.0,
}
_LOW_VOLATILITY_CONFIDENCE = {
    VolatilityRegimeState.LOW: 60.0,
    VolatilityRegimeState.VERY_LOW: 80.0,
}
_BREAKOUT_BASE_CONFIDENCE = 70.0
_BREAKOUT_VOLUME_BONUS = 20.0


def build_candidates(
    trend_regime: TrendRegimeEvidence,
    volatility: VolatilityRegimeEvidence,
    range_evidence: RangeEvidence,
    accumulation_distribution: AccumulationDistributionEvidence,
    breakout: BreakoutEvidence,
    pullback_reversal: PullbackReversalEvidence,
) -> list[RegimeCandidate]:
    candidates: list[RegimeCandidate] = []

    reversal_confidence = pullback_reversal.reversal_confidence or 0.0
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.REVERSAL, reversal_confidence, _PRECEDENCE[MarketRegimeState.REVERSAL]
        )
    )

    if breakout.detected and breakout.direction != BreakoutDirection.FALSE_BREAKOUT:
        breakout_confidence = _BREAKOUT_BASE_CONFIDENCE + (
            _BREAKOUT_VOLUME_BONUS if breakout.volume_confirmed else 0.0
        )
    else:
        breakout_confidence = 0.0
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.BREAKOUT, breakout_confidence, _PRECEDENCE[MarketRegimeState.BREAKOUT]
        )
    )

    candidates.append(
        RegimeCandidate(
            MarketRegimeState.ACCUMULATION,
            accumulation_distribution.accumulation_score,
            _PRECEDENCE[MarketRegimeState.ACCUMULATION],
        )
    )
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.DISTRIBUTION,
            accumulation_distribution.distribution_score,
            _PRECEDENCE[MarketRegimeState.DISTRIBUTION],
        )
    )

    trend_base = TREND_STRENGTH_BASE.get(trend_regime.strength, 0.0)
    alignment_bonus = ALIGNMENT_BONUS if trend_regime.aligned else 0.0
    bullish_confidence = (
        min(100.0, trend_base + alignment_bonus)
        if trend_regime.direction == TrendDirection.BULLISH
        else 0.0
    )
    bearish_confidence = (
        min(100.0, trend_base + alignment_bonus)
        if trend_regime.direction == TrendDirection.BEARISH
        else 0.0
    )
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.TRENDING_BULLISH,
            bullish_confidence,
            _PRECEDENCE[MarketRegimeState.TRENDING_BULLISH],
        )
    )
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.TRENDING_BEARISH,
            bearish_confidence,
            _PRECEDENCE[MarketRegimeState.TRENDING_BEARISH],
        )
    )

    pullback_confidence = (
        _PULLBACK_CONFIDENCE.get(pullback_reversal.pullback_depth, 0.0)
        if pullback_reversal.pullback_depth is not None
        else 0.0
    )
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.PULLBACK, pullback_confidence, _PRECEDENCE[MarketRegimeState.PULLBACK]
        )
    )

    ranging_confidence = (
        _RANGE_STRENGTH_CONFIDENCE.get(range_evidence.range_strength or "", 0.0)
        if range_evidence.is_ranging
        else 0.0
    )
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.RANGING, ranging_confidence, _PRECEDENCE[MarketRegimeState.RANGING]
        )
    )

    candidates.append(
        RegimeCandidate(
            MarketRegimeState.HIGH_VOLATILITY,
            _HIGH_VOLATILITY_CONFIDENCE.get(volatility.state, 0.0),
            _PRECEDENCE[MarketRegimeState.HIGH_VOLATILITY],
        )
    )
    candidates.append(
        RegimeCandidate(
            MarketRegimeState.LOW_VOLATILITY,
            _LOW_VOLATILITY_CONFIDENCE.get(volatility.state, 0.0),
            _PRECEDENCE[MarketRegimeState.LOW_VOLATILITY],
        )
    )

    return candidates


@dataclass(frozen=True, slots=True)
class ClassificationOutcome:
    regime: MarketRegimeState
    winner: RegimeCandidate | None
    runner_up: RegimeCandidate | None
    candidates: list[RegimeCandidate] = field(default_factory=list)
    stability_penalty: float = 0.0
    warnings: list[str] = field(default_factory=list)


def classify(candidates: list[RegimeCandidate]) -> ClassificationOutcome:
    qualifying = [c for c in candidates if c.confidence >= MIN_CONFIDENCE_TO_QUALIFY]
    if not qualifying:
        return ClassificationOutcome(
            regime=MarketRegimeState.UNCERTAIN, winner=None, runner_up=None, candidates=candidates
        )

    qualifying_sorted = sorted(qualifying, key=lambda c: (c.precedence, -c.confidence))
    winner = qualifying_sorted[0]
    others = [c for c in qualifying if c.regime != winner.regime]
    runner_up = max(others, key=lambda c: c.confidence) if others else None

    stability_penalty = 0.0
    warnings: list[str] = []
    if runner_up is not None:
        margin = winner.confidence - runner_up.confidence
        if margin < MIN_MARGIN:
            stability_penalty = -(MIN_MARGIN - margin)
            warnings.append(
                f"Regime classification margin is thin between {winner.regime.value} "
                f"and {runner_up.regime.value} - treat with caution"
            )

    return ClassificationOutcome(
        regime=winner.regime,
        winner=winner,
        runner_up=runner_up,
        candidates=candidates,
        stability_penalty=stability_penalty,
        warnings=warnings,
    )

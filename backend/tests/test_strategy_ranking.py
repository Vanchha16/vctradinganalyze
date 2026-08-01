from app.services.strategy.ranking import rank, rejection_reason
from app.services.strategy.types import StrategyBreakdown, StrategyName


def _breakdown(
    market_match: float = 30.0,
    evidence_quality: float = 20.0,
    confidence: float = 17.0,
    risk: float = 15.0,
    historical_performance: float = 5.0,
) -> StrategyBreakdown:
    return StrategyBreakdown(
        market_match=market_match,
        evidence_quality=evidence_quality,
        confidence=confidence,
        risk=risk,
        historical_performance=historical_performance,
    )


def test_rejection_reason_none_for_a_strong_breakdown() -> None:
    breakdown = _breakdown()
    assert rejection_reason(StrategyName.TREND_FOLLOWING, breakdown) is None


def test_rejection_reason_market_match_zero() -> None:
    breakdown = _breakdown(market_match=0.0)
    reason = rejection_reason(StrategyName.MEAN_REVERSION, breakdown)
    assert reason is not None
    assert "incompatible" in reason


def test_rejection_reason_below_minimum_total() -> None:
    breakdown = _breakdown(
        market_match=30.0,
        evidence_quality=0.0,
        confidence=0.0,
        risk=0.0,
        historical_performance=0.0,
    )
    reason = rejection_reason(StrategyName.TREND_FOLLOWING, breakdown)
    assert reason is not None
    assert "minimum threshold" in reason


def test_rank_picks_highest_scoring_as_primary() -> None:
    scores = {strategy: _breakdown(market_match=0.0) for strategy in StrategyName}
    scores[StrategyName.TREND_FOLLOWING] = _breakdown(evidence_quality=25.0)
    scores[StrategyName.SMC] = _breakdown(evidence_quality=20.0)

    primary, primary_breakdown, alternatives, rejected = rank(scores)

    assert primary is StrategyName.TREND_FOLLOWING
    assert primary_breakdown is not None
    assert any(a.strategy is StrategyName.SMC for a in alternatives)
    assert len(rejected) == len(StrategyName) - 2


def test_rank_returns_none_primary_when_all_rejected() -> None:
    scores = {strategy: _breakdown(market_match=0.0) for strategy in StrategyName}
    primary, primary_breakdown, alternatives, rejected = rank(scores)
    assert primary is None
    assert primary_breakdown is None
    assert alternatives == []
    assert len(rejected) == len(StrategyName)


def test_rank_ties_broken_by_declaration_order() -> None:
    scores = {strategy: _breakdown() for strategy in StrategyName}
    primary, _, alternatives, _ = rank(scores)
    assert primary is StrategyName.TREND_FOLLOWING  # first in declaration order
    ordered_alternatives = [a.strategy for a in alternatives]
    declaration_order = [s for s in StrategyName if s is not StrategyName.TREND_FOLLOWING]
    assert ordered_alternatives == declaration_order

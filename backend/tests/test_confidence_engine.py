from app.services.market_regime import confidence_engine
from app.services.market_regime.regime_classifier import ClassificationOutcome
from app.services.market_regime.types import (
    MarketRegimeState,
    RegimeCandidate,
    RegimeConflictReport,
    TrendRegimeEvidence,
    VolatilityRegimeEvidence,
    VolatilityRegimeState,
)
from app.services.smc.types import MarketStructureState
from app.services.technical_analysis.types import TrendDirection, TrendStrengthLevel


def _trend_regime(strength: TrendStrengthLevel, aligned: bool) -> TrendRegimeEvidence:
    return TrendRegimeEvidence(
        direction=TrendDirection.BULLISH,
        strength=strength,
        structure_state=MarketStructureState.BULLISH,
        aligned=aligned,
    )


def test_strong_aligned_trend_and_no_conflicts_scores_high() -> None:
    trend_regime = _trend_regime(TrendStrengthLevel.VERY_STRONG, aligned=True)
    volatility = VolatilityRegimeEvidence(
        state=VolatilityRegimeState.HIGH, recent_atr_average=2.0, baseline_atr_average=1.0
    )
    winner = RegimeCandidate(MarketRegimeState.TRENDING_BULLISH, 95.0, 4)
    outcome = ClassificationOutcome(
        regime=MarketRegimeState.TRENDING_BULLISH, winner=winner, runner_up=None
    )

    breakdown = confidence_engine.score(trend_regime, volatility, outcome, RegimeConflictReport())

    assert breakdown.total > 70.0
    assert breakdown.stability_penalty == 0.0
    assert breakdown.conflict_penalty == 0.0


def test_uncertain_outcome_scores_low() -> None:
    trend_regime = _trend_regime(TrendStrengthLevel.WEAK, aligned=False)
    volatility = VolatilityRegimeEvidence(
        state=VolatilityRegimeState.NORMAL, recent_atr_average=1.0, baseline_atr_average=1.0
    )
    outcome = ClassificationOutcome(regime=MarketRegimeState.UNCERTAIN, winner=None, runner_up=None)

    breakdown = confidence_engine.score(trend_regime, volatility, outcome, RegimeConflictReport())

    assert breakdown.structural_confirmation == 0.0


def test_conflicts_reduce_confidence() -> None:
    from app.services.market_regime.types import RegimeConflict

    trend_regime = _trend_regime(TrendStrengthLevel.STRONG, aligned=True)
    volatility = VolatilityRegimeEvidence(
        state=VolatilityRegimeState.NORMAL, recent_atr_average=1.0, baseline_atr_average=1.0
    )
    winner = RegimeCandidate(MarketRegimeState.TRENDING_BULLISH, 80.0, 4)
    outcome = ClassificationOutcome(
        regime=MarketRegimeState.TRENDING_BULLISH, winner=winner, runner_up=None
    )
    conflicts = RegimeConflictReport(conflicts=[RegimeConflict("something disagrees")])

    with_conflict = confidence_engine.score(trend_regime, volatility, outcome, conflicts)
    without_conflict = confidence_engine.score(
        trend_regime, volatility, outcome, RegimeConflictReport()
    )

    assert with_conflict.total < without_conflict.total

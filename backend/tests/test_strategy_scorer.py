from dataclasses import replace

from app.models.enums import Timeframe
from app.services.market_regime.types import VolatilityRegimeEvidence, VolatilityRegimeState
from app.services.risk_management.economic_filter import EconomicFilterResult
from app.services.risk_management.types import LiquidityClassification, MarketSession
from app.services.strategy import strategy_scorer
from app.services.strategy.types import StrategyName
from tests.analysis_confidence_helpers import make_regime_result
from tests.strategy_helpers import make_evidence_bundle


def test_score_returns_all_five_components() -> None:
    evidence = make_evidence_bundle()
    breakdown = strategy_scorer.score(StrategyName.TREND_FOLLOWING, evidence, Timeframe.H1)
    assert breakdown.market_match >= 0
    assert breakdown.evidence_quality >= 0
    assert breakdown.confidence >= 0
    assert breakdown.risk >= 0
    assert breakdown.historical_performance == 5.0


def test_score_risk_component_reduced_when_session_closed() -> None:
    evidence_open = make_evidence_bundle(session=MarketSession.LONDON)
    evidence_closed = make_evidence_bundle(session=MarketSession.CLOSED)

    breakdown_open = strategy_scorer.score(
        StrategyName.TREND_FOLLOWING, evidence_open, Timeframe.H1
    )
    breakdown_closed = strategy_scorer.score(
        StrategyName.TREND_FOLLOWING, evidence_closed, Timeframe.H1
    )

    assert breakdown_closed.risk < breakdown_open.risk


def test_score_risk_component_stacks_every_penalty() -> None:
    regime = make_regime_result()
    extreme_volatility_regime = replace(
        regime,
        volatility=VolatilityRegimeEvidence(
            state=VolatilityRegimeState.EXTREME, recent_atr_average=1.0, baseline_atr_average=1.0
        ),
    )
    evidence = make_evidence_bundle(
        market_regime=extreme_volatility_regime,
        session=MarketSession.CLOSED,
        liquidity=LiquidityClassification.LOW,
        economic=EconomicFilterResult(economic_score=0.0, hard_reject=True, reason="critical"),
    )
    breakdown = strategy_scorer.score(StrategyName.TREND_FOLLOWING, evidence, Timeframe.H1)
    # 15 base - 3 (closed) - 3 (low liquidity) - 5 (critical event) - 3 (extreme volatility) = 1.
    assert breakdown.risk == 1.0


def test_score_total_capped_at_100() -> None:
    evidence = make_evidence_bundle(overall_confidence=100.0)
    breakdown = strategy_scorer.score(StrategyName.TREND_FOLLOWING, evidence, Timeframe.H1)
    assert breakdown.total <= 100.0

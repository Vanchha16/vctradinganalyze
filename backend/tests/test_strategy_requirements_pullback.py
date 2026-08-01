from dataclasses import replace
from decimal import Decimal

from app.services.market_regime.types import (
    MarketRegimeResult,
    PullbackDepth,
    PullbackReversalEvidence,
)
from app.services.strategy.requirements.pullback import check
from app.services.technical_analysis.types import (
    SupportResistanceLevel,
    TechnicalAnalysisResult,
    TrendStrengthLevel,
)
from tests.analysis_confidence_helpers import make_regime_result, make_technical_result
from tests.strategy_helpers import make_evidence_bundle


def _regime_with_pullback(
    depth: PullbackDepth | None, reversal_confidence: float | None
) -> MarketRegimeResult:
    regime = make_regime_result()
    return replace(
        regime,
        pullback_reversal=PullbackReversalEvidence(
            pullback_depth=depth,
            retracement_ratio=0.5 if depth is not None else None,
            reversal_direction=None,
            reversal_confidence=reversal_confidence,
            exhaustion_warning=None,
        ),
    )


def _technical_with_strong_trend() -> TechnicalAnalysisResult:
    technical = make_technical_result()
    return replace(
        technical,
        trend_evidence=replace(technical.trend_evidence, strength=TrendStrengthLevel.VERY_STRONG),
        support=SupportResistanceLevel(
            price=Decimal("1.1000"), source="swing_low", strength="strong"
        ),
    )


def test_check_full_pullback_setup() -> None:
    regime = _regime_with_pullback(PullbackDepth.HEALTHY, 0.8)
    technical = _technical_with_strong_trend()
    evidence = make_evidence_bundle(market_regime=regime, technical=technical)
    result = check(evidence)
    assert result.met_count == 4
    assert result.total_count == 4


def test_check_no_pullback_detected() -> None:
    regime = _regime_with_pullback(None, None)
    evidence = make_evidence_bundle(market_regime=regime)
    result = check(evidence)
    assert result.met_count < 4


def test_check_no_evidence_gives_zero_met() -> None:
    evidence = make_evidence_bundle(include_evidence=False)
    result = check(evidence)
    assert result.met_count == 0
    assert result.total_count == 4

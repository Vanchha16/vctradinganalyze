from dataclasses import replace
from decimal import Decimal

from app.services.market_regime.types import MarketRegimeResult, RangeEvidence
from app.services.strategy.requirements.mean_reversion import check
from app.services.technical_analysis.types import (
    SupportResistanceLevel,
    TechnicalAnalysisResult,
    TrendStrengthLevel,
)
from tests.analysis_confidence_helpers import make_regime_result, make_technical_result
from tests.strategy_helpers import make_evidence_bundle


def _ranging_regime() -> MarketRegimeResult:
    regime = make_regime_result()
    return replace(
        regime, range=RangeEvidence(is_ranging=True, range_width=None, range_strength="strong")
    )


def _low_trend_technical() -> TechnicalAnalysisResult:
    technical = make_technical_result()
    return replace(
        technical,
        trend_evidence=replace(technical.trend_evidence, strength=TrendStrengthLevel.WEAK),
        support=SupportResistanceLevel(
            price=Decimal("1.0900"), source="swing_low", strength="strong"
        ),
        resistance=SupportResistanceLevel(
            price=Decimal("1.1100"), source="swing_high", strength="strong"
        ),
    )


def test_check_full_mean_reversion_setup() -> None:
    regime = _ranging_regime()
    technical = _low_trend_technical()
    evidence = make_evidence_bundle(market_regime=regime, technical=technical)
    result = check(evidence)
    assert result.met_count == 4
    assert result.total_count == 4


def test_check_trending_market_reduces_matches() -> None:
    evidence = make_evidence_bundle()  # default is trending, strong support/resistance
    result = check(evidence)
    assert result.met_count < 4


def test_check_no_evidence_gives_zero_met() -> None:
    evidence = make_evidence_bundle(include_evidence=False)
    result = check(evidence)
    assert result.met_count == 0
    assert result.total_count == 4

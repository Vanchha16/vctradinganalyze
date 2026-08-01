from app.services.market_regime.types import VolatilityRegimeState
from app.services.risk_management.decision import (
    is_approved,
    position_guidance_for,
    risk_level_for,
    tier_for_score,
)
from app.services.risk_management.types import PositionGuidance, RiskLevel, TradeQualityTier


def test_tier_for_score_boundaries() -> None:
    assert tier_for_score(90.0) == TradeQualityTier.EXCELLENT
    assert tier_for_score(89.9) == TradeQualityTier.VERY_GOOD
    assert tier_for_score(80.0) == TradeQualityTier.VERY_GOOD
    assert tier_for_score(79.9) == TradeQualityTier.GOOD
    assert tier_for_score(70.0) == TradeQualityTier.GOOD
    assert tier_for_score(69.9) == TradeQualityTier.AVERAGE
    assert tier_for_score(60.0) == TradeQualityTier.AVERAGE
    assert tier_for_score(59.9) == TradeQualityTier.REJECT


def test_is_approved_false_when_hard_reject_reasons_present() -> None:
    assert is_approved(["extreme volatility"], TradeQualityTier.EXCELLENT) is False


def test_is_approved_false_when_score_tier_is_reject() -> None:
    assert is_approved([], TradeQualityTier.REJECT) is False


def test_is_approved_true_when_no_reasons_and_tier_above_reject() -> None:
    assert is_approved([], TradeQualityTier.AVERAGE) is True


def test_is_approved_collects_multiple_reasons_upstream() -> None:
    """decision.py itself just checks non-emptiness - the caller
    (RiskManagementEngine) is responsible for collecting every reason,
    not just the first (ADR-068)."""
    assert is_approved(["reason a", "reason b"], TradeQualityTier.EXCELLENT) is False


def test_risk_level_low_for_low_volatility_and_strong_tier() -> None:
    result = risk_level_for(VolatilityRegimeState.LOW, TradeQualityTier.EXCELLENT)
    assert result == RiskLevel.LOW


def test_risk_level_high_for_extreme_volatility() -> None:
    result = risk_level_for(VolatilityRegimeState.EXTREME, TradeQualityTier.EXCELLENT)
    assert result == RiskLevel.HIGH


def test_risk_level_high_for_average_tier_regardless_of_volatility() -> None:
    result = risk_level_for(VolatilityRegimeState.VERY_LOW, TradeQualityTier.AVERAGE)
    assert result == RiskLevel.HIGH


def test_risk_level_medium_otherwise() -> None:
    result = risk_level_for(VolatilityRegimeState.NORMAL, TradeQualityTier.GOOD)
    assert result == RiskLevel.MEDIUM


def test_position_guidance_none_when_not_approved() -> None:
    assert position_guidance_for(False, TradeQualityTier.EXCELLENT, RiskLevel.LOW) is None


def test_position_guidance_aggressive_for_excellent_low_risk() -> None:
    result = position_guidance_for(True, TradeQualityTier.EXCELLENT, RiskLevel.LOW)
    assert result == PositionGuidance.AGGRESSIVE


def test_position_guidance_normal_for_strong_tiers_otherwise() -> None:
    result = position_guidance_for(True, TradeQualityTier.EXCELLENT, RiskLevel.MEDIUM)
    assert result == PositionGuidance.NORMAL
    result2 = position_guidance_for(True, TradeQualityTier.VERY_GOOD, RiskLevel.MEDIUM)
    assert result2 == PositionGuidance.NORMAL


def test_position_guidance_conservative_for_good_tier() -> None:
    result = position_guidance_for(True, TradeQualityTier.GOOD, RiskLevel.MEDIUM)
    assert result == PositionGuidance.CONSERVATIVE


def test_position_guidance_very_conservative_for_average_tier() -> None:
    result = position_guidance_for(True, TradeQualityTier.AVERAGE, RiskLevel.MEDIUM)
    assert result == PositionGuidance.VERY_CONSERVATIVE

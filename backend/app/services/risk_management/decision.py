"""Deterministic decision logic (docs/12 §16, docs/48 §8, ADR-068).
Hard-reject rules are evaluated independently of and before the
score-tier Decision Matrix - honors ADR-014's pre-existing "Risk Engine
has veto authority." All triggered hard-reject reasons are collected
(not first-match), and `trade_quality` is always computed regardless
(explainability, ADR-041 extended)."""

from app.services.market_regime.types import VolatilityRegimeState
from app.services.risk_management.types import PositionGuidance, RiskLevel, TradeQualityTier

_EXCELLENT_MIN = 90.0
_VERY_GOOD_MIN = 80.0
_GOOD_MIN = 70.0
_AVERAGE_MIN = 60.0

_LOW_RISK_VOLATILITY = frozenset({VolatilityRegimeState.VERY_LOW, VolatilityRegimeState.LOW})
_HIGH_RISK_VOLATILITY = frozenset({VolatilityRegimeState.HIGH, VolatilityRegimeState.EXTREME})
_HIGH_RISK_TIERS = frozenset({TradeQualityTier.AVERAGE, TradeQualityTier.REJECT})
_STRONG_TIERS = frozenset({TradeQualityTier.EXCELLENT, TradeQualityTier.VERY_GOOD})


def tier_for_score(total: float) -> TradeQualityTier:
    if total >= _EXCELLENT_MIN:
        return TradeQualityTier.EXCELLENT
    if total >= _VERY_GOOD_MIN:
        return TradeQualityTier.VERY_GOOD
    if total >= _GOOD_MIN:
        return TradeQualityTier.GOOD
    if total >= _AVERAGE_MIN:
        return TradeQualityTier.AVERAGE
    return TradeQualityTier.REJECT


def is_approved(rejected_reasons: list[str], tier: TradeQualityTier) -> bool:
    return not rejected_reasons and tier is not TradeQualityTier.REJECT


def risk_level_for(
    volatility_state: VolatilityRegimeState | None, tier: TradeQualityTier
) -> RiskLevel:
    if volatility_state in _HIGH_RISK_VOLATILITY or tier in _HIGH_RISK_TIERS:
        return RiskLevel.HIGH
    if volatility_state in _LOW_RISK_VOLATILITY and tier in _STRONG_TIERS:
        return RiskLevel.LOW
    return RiskLevel.MEDIUM


def position_guidance_for(
    approved: bool, tier: TradeQualityTier, risk_level: RiskLevel
) -> PositionGuidance | None:
    if not approved:
        return None
    if tier is TradeQualityTier.EXCELLENT and risk_level is RiskLevel.LOW:
        return PositionGuidance.AGGRESSIVE
    if tier in _STRONG_TIERS:
        return PositionGuidance.NORMAL
    if tier is TradeQualityTier.GOOD:
        return PositionGuidance.CONSERVATIVE
    if tier is TradeQualityTier.AVERAGE:
        return PositionGuidance.VERY_CONSERVATIVE
    return None

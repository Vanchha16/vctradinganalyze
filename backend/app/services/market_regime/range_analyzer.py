"""docs/16 §7 Range Detection: reuses Technical Analysis's
`SupportResistanceEvidence` (nearest support/resistance) directly -
no re-detection of levels. "Flat EMA"/"Weak ADX"/"Low Momentum" are
already captured by `TrendEvidence.strength`/`direction`.
"""

from decimal import Decimal

from app.services.market_regime.types import RangeEvidence
from app.services.technical_analysis.types import (
    SupportResistanceLevel,
    TrendDirection,
    TrendEvidence,
    TrendStrengthLevel,
)

_TIGHT_RANGE_RATIO = Decimal("0.01")
_MODERATE_RANGE_RATIO = Decimal("0.03")


def analyze(
    trend_evidence: TrendEvidence,
    support: SupportResistanceLevel | None,
    resistance: SupportResistanceLevel | None,
    current_price: Decimal,
) -> RangeEvidence:
    if support is None or resistance is None or resistance.price <= support.price:
        return RangeEvidence(is_ranging=False, range_width=None, range_strength=None)

    price_within_range = support.price <= current_price <= resistance.price
    weak_trend = (
        trend_evidence.strength == TrendStrengthLevel.WEAK
        or trend_evidence.direction == TrendDirection.SIDEWAYS
    )
    is_ranging = price_within_range and weak_trend

    if not is_ranging:
        return RangeEvidence(is_ranging=False, range_width=None, range_strength=None)

    range_width = resistance.price - support.price
    ratio = range_width / current_price if current_price > 0 else Decimal("0")

    if ratio < _TIGHT_RANGE_RATIO:
        range_strength = "strong"
    elif ratio < _MODERATE_RANGE_RATIO:
        range_strength = "moderate"
    else:
        range_strength = "weak"

    return RangeEvidence(is_ranging=True, range_width=range_width, range_strength=range_strength)

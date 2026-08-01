"""Deterministic market bias rule table (docs/14 §7, docs/47 §6,
ADR-060). Generalizes docs/14 §7's CPI worked example across all 7
categories. "Potentially" language only - never a BUY/SELL/WAIT
recommendation. Only the INFLATION row is sourced directly from docs/14;
every other row is this project's own hand-tuned starting point (ADR-060),
not an empirically calibrated model."""

from app.models.enums import EconomicEventCategory
from app.services.economic_calendar.types import MarketBias, SurpriseDirection

_BULLISH_ON_STRONG = frozenset(
    {
        EconomicEventCategory.INFLATION,
        EconomicEventCategory.CENTRAL_BANK,
        EconomicEventCategory.EMPLOYMENT,
        EconomicEventCategory.GROWTH,
        EconomicEventCategory.CONSUMER,
        EconomicEventCategory.HOUSING,
    }
)

# Whether "stronger/higher than forecast" reads as risk-positive
# (equities up) or risk-negative (equities down) for this category.
_RISK_POSITIVE_ON_STRONG = frozenset(
    {
        EconomicEventCategory.EMPLOYMENT,
        EconomicEventCategory.GROWTH,
        EconomicEventCategory.CONSUMER,
        EconomicEventCategory.HOUSING,
    }
)

_GOLD_NEUTRAL_CATEGORIES = frozenset({EconomicEventCategory.HOUSING})

_NEUTRAL_BIAS: dict[str, MarketBias] = {
    "currency": MarketBias.NEUTRAL,
    "gold": MarketBias.NEUTRAL,
    "equities": MarketBias.NEUTRAL,
}


def analyze(
    category: EconomicEventCategory, surprise_direction: SurpriseDirection
) -> dict[str, MarketBias]:
    if surprise_direction is SurpriseDirection.IN_LINE:
        return dict(_NEUTRAL_BIAS)
    if category is EconomicEventCategory.OTHER:
        return dict(_NEUTRAL_BIAS)
    if category not in _BULLISH_ON_STRONG:
        return dict(_NEUTRAL_BIAS)

    is_strong = surprise_direction is SurpriseDirection.HIGHER_THAN_FORECAST
    currency_bias = MarketBias.POTENTIALLY_BULLISH if is_strong else MarketBias.POTENTIALLY_BEARISH

    if category in _GOLD_NEUTRAL_CATEGORIES:
        gold_bias = MarketBias.NEUTRAL
    else:
        gold_bias = MarketBias.POTENTIALLY_BEARISH if is_strong else MarketBias.POTENTIALLY_BULLISH

    risk_positive_on_strong = category in _RISK_POSITIVE_ON_STRONG
    equities_strong_bias = (
        MarketBias.POTENTIALLY_BULLISH
        if risk_positive_on_strong
        else MarketBias.POTENTIALLY_BEARISH
    )
    equities_weak_bias = (
        MarketBias.POTENTIALLY_BEARISH
        if risk_positive_on_strong
        else MarketBias.POTENTIALLY_BULLISH
    )
    equities_bias = equities_strong_bias if is_strong else equities_weak_bias

    return {"currency": currency_bias, "gold": gold_bias, "equities": equities_bias}

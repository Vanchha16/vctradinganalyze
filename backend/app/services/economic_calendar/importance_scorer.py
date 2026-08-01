"""Deterministic importance scoring (docs/14 §4, docs/47 §5, ADR-059).
Event-name overrides checked first, then category defaults - first
match wins. No source-tier axis (unlike News's importance_scorer),
since economic data has one canonical value per event."""

from app.models.enums import EconomicEventCategory, EconomicEventImportance

_CRITICAL_EVENT_NAME_KEYWORDS = (
    "fomc",
    "interest rate decision",
    "non-farm payroll",
    "nonfarm payroll",
    "non farm payroll",
    "nfp",
    "cpi",
    "core cpi",
    "gdp",
)
_HIGH_CATEGORIES = {
    EconomicEventCategory.CENTRAL_BANK,
    EconomicEventCategory.GROWTH,
    EconomicEventCategory.INFLATION,
    EconomicEventCategory.EMPLOYMENT,
    EconomicEventCategory.CONSUMER,
}
_MEDIUM_OTHER_EVENT_NAME_KEYWORDS = (
    "trade balance",
    "current account",
    "manufacturing pmi",
    "services pmi",
)


def score(category: EconomicEventCategory, event_name: str) -> EconomicEventImportance:
    text = event_name.lower()

    if any(keyword in text for keyword in _CRITICAL_EVENT_NAME_KEYWORDS):
        return EconomicEventImportance.CRITICAL
    if category in _HIGH_CATEGORIES:
        return EconomicEventImportance.HIGH
    if category is EconomicEventCategory.HOUSING:
        return EconomicEventImportance.MEDIUM
    if category is EconomicEventCategory.OTHER and any(
        keyword in text for keyword in _MEDIUM_OTHER_EVENT_NAME_KEYWORDS
    ):
        return EconomicEventImportance.MEDIUM
    return EconomicEventImportance.LOW

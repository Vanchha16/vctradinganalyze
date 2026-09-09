"""Deterministic importance scoring (docs/14 §4, docs/47 §5, ADR-059).
Event-name overrides checked first, then category defaults - first
match wins. No source-tier axis (unlike News's importance_scorer),
since economic data has one canonical value per event."""

from app.models.enums import EconomicEventCategory, EconomicEventImportance

#: ADR-150 added ForexFactory's names for these same releases. A rate
#: decision it calls "Federal Funds Rate" or "Main Refinancing Rate" was
#: scoring LOW, which is the one error this scorer must not make: LOW is
#: what lets `economic_filter` allow a trade through.
#:
#: "employment change" deliberately also catches ADP's release, which is
#: a forecast of NFP rather than NFP itself. Over-scoring it means one
#: extra blackout window; under-scoring the real NFP means trading into
#: it. Those are not symmetric.
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
    "federal funds rate",
    "main refinancing rate",
    "official bank rate",
    "official cash rate",
    "cash rate",
    "overnight rate",
    "policy rate",
    "monetary policy statement",
    "rate statement",
    "employment change",
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

"""Deterministic category classification (docs/14 §3, docs/47 §5,
ADR-059). Keyword match against `event_name` - first match wins,
evaluated in a fixed order. Specific "Other"-bucket PMI variants are
checked *before* the generic "PMI" keyword (docs/14 §3 lists both
"PMI" under Growth and "Manufacturing PMI"/"Services PMI" under Other).
No ML/LLM involved."""

from app.models.enums import EconomicEventCategory

_CATEGORY_KEYWORDS: list[tuple[EconomicEventCategory, tuple[str, ...]]] = [
    (
        EconomicEventCategory.CENTRAL_BANK,
        ("fomc", "interest rate decision", "ecb", "boe", "boj", "rba", "rbnz", "boc", "snb"),
    ),
    (
        EconomicEventCategory.INFLATION,
        ("cpi", "core cpi", "ppi", "core ppi", "consumer price", "producer price"),
    ),
    (
        EconomicEventCategory.EMPLOYMENT,
        (
            "non-farm payroll",
            "nonfarm payroll",
            "non farm payroll",
            "unemployment rate",
            "average hourly earnings",
            "jobless claims",
        ),
    ),
    (
        EconomicEventCategory.HOUSING,
        ("building permits", "housing starts", "existing home sales"),
    ),
    (
        EconomicEventCategory.CONSUMER,
        ("consumer confidence", "consumer sentiment"),
    ),
    (
        EconomicEventCategory.OTHER,
        ("trade balance", "current account", "manufacturing pmi", "services pmi"),
    ),
    (
        EconomicEventCategory.GROWTH,
        ("gdp", "retail sales", "pmi", "industrial production"),
    ),
]

_DEFAULT_CATEGORY = EconomicEventCategory.OTHER


def classify(event_name: str) -> EconomicEventCategory:
    text = event_name.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    return _DEFAULT_CATEGORY

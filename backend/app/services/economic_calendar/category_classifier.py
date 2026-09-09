"""Deterministic category classification (docs/14 §3, docs/47 §5,
ADR-059). Keyword match against `event_name` - first match wins,
evaluated in a fixed order.

ADR-150 extended these lists with ForexFactory's naming. The keywords
below were written against Finnhub's names, and ForexFactory calls the
same releases something else: the Fed decision is "Federal Funds Rate",
the ECB's is "Main Refinancing Rate", NFP is "Non-Farm Employment
Change", jobless claims are "Unemployment Claims". Measured against a
real week of the feed, every one of those fell through to OTHER/LOW -
meaning the risk filter would have let a trade run straight into an ECB
rate decision. Specific "Other"-bucket PMI variants are
checked *before* the generic "PMI" keyword (docs/14 §3 lists both
"PMI" under Growth and "Manufacturing PMI"/"Services PMI" under Other).
No ML/LLM involved."""

from app.models.enums import EconomicEventCategory

_CATEGORY_KEYWORDS: list[tuple[EconomicEventCategory, tuple[str, ...]]] = [
    (
        EconomicEventCategory.CENTRAL_BANK,
        (
            "fomc",
            "interest rate decision",
            "ecb",
            "boe",
            "boj",
            "rba",
            "rbnz",
            "boc",
            "snb",
            # ADR-150 - ForexFactory names a rate decision after the
            # rate itself rather than after the committee.
            "federal funds rate",
            "main refinancing rate",
            "official bank rate",
            "official cash rate",
            "cash rate",
            "overnight rate",
            "policy rate",
            "monetary policy statement",
            "monetary policy report",
            "rate statement",
            "meeting minutes",
        ),
    ),
    (
        EconomicEventCategory.INFLATION,
        (
            "cpi",
            "core cpi",
            "ppi",
            "core ppi",
            "consumer price",
            "producer price",
            # ADR-150 - "Prelim UoM Inflation Expectations".
            "inflation expectations",
        ),
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
            # ADR-150 - ForexFactory's names for the same releases.
            "non-farm employment change",
            "employment change",
            "unemployment claims",
            "claimant count",
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

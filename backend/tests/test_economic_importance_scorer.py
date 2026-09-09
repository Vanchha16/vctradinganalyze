import pytest

from app.models.enums import EconomicEventCategory, EconomicEventImportance
from app.services.economic_calendar.importance_scorer import score


@pytest.mark.parametrize(
    ("category", "event_name", "expected"),
    [
        # docs/14 §4 worked examples: FOMC/Rate Decision/NFP/CPI/GDP -> Critical.
        (
            EconomicEventCategory.CENTRAL_BANK,
            "FOMC Interest Rate Decision",
            EconomicEventImportance.CRITICAL,
        ),
        (EconomicEventCategory.EMPLOYMENT, "Non-Farm Payrolls", EconomicEventImportance.CRITICAL),
        (EconomicEventCategory.INFLATION, "CPI y/y", EconomicEventImportance.CRITICAL),
        (EconomicEventCategory.GROWTH, "GDP q/q", EconomicEventImportance.CRITICAL),
        # docs/14 §4: PMI/Retail Sales/Consumer Confidence -> High.
        (EconomicEventCategory.GROWTH, "PMI", EconomicEventImportance.HIGH),
        (EconomicEventCategory.GROWTH, "Retail Sales m/m", EconomicEventImportance.HIGH),
        (EconomicEventCategory.CONSUMER, "Consumer Confidence", EconomicEventImportance.HIGH),
        # Not overridden to Critical - falls through to category default High.
        (EconomicEventCategory.INFLATION, "Core PPI m/m", EconomicEventImportance.HIGH),
        (EconomicEventCategory.EMPLOYMENT, "Unemployment Rate", EconomicEventImportance.HIGH),
        (EconomicEventCategory.CENTRAL_BANK, "ECB Press Conference", EconomicEventImportance.HIGH),
        # docs/14 §4: Housing/Trade Balance -> Medium.
        (EconomicEventCategory.HOUSING, "Building Permits", EconomicEventImportance.MEDIUM),
        (EconomicEventCategory.OTHER, "Trade Balance", EconomicEventImportance.MEDIUM),
        (EconomicEventCategory.OTHER, "Manufacturing PMI", EconomicEventImportance.MEDIUM),
        # docs/14 §4: minor reports -> Low.
        (
            EconomicEventCategory.OTHER,
            "Some Unrecognized Minor Report",
            EconomicEventImportance.LOW,
        ),
    ],
)
def test_score_matches_rule_table(
    category: EconomicEventCategory, event_name: str, expected: EconomicEventImportance
) -> None:
    assert score(category, event_name) == expected


@pytest.mark.parametrize(
    "event_name",
    [
        "Federal Funds Rate",
        "Main Refinancing Rate",
        "Official Bank Rate",
        "Official Cash Rate",
        "Cash Rate",
        "Overnight Rate",
        "SNB Policy Rate",
        "Monetary Policy Statement",
        "RBA Rate Statement",
        "Non-Farm Employment Change",
    ],
)
def test_forexfactory_named_rate_decisions_score_critical(event_name: str) -> None:
    """ADR-150 - these are the releases the calendar exists to block
    around. Under ForexFactory's naming they scored LOW, and LOW is
    precisely what lets `economic_filter` wave a trade through."""
    assert score(EconomicEventCategory.CENTRAL_BANK, event_name) is EconomicEventImportance.CRITICAL


def test_a_policy_report_hearing_is_high_not_critical() -> None:
    """A hearing about past policy is not a rate decision. It still
    moves price, so it is not LOW either - the distinction is why
    "monetary policy report" is a category keyword rather than a
    critical-name override."""
    assert (
        score(EconomicEventCategory.CENTRAL_BANK, "Monetary Policy Report Hearings")
        is EconomicEventImportance.HIGH
    )

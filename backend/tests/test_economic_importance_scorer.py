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

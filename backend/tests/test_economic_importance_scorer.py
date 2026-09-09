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


def test_the_weekly_adp_series_does_not_hard_reject_signals() -> None:
    """Found in production the day ADR-150 deployed: a bare "employment
    change" keyword scored "ADP Weekly Employment Change" CRITICAL, and
    CRITICAL inside a risk window is a *hard reject* - so a release the
    feed itself marks Low would have blocked every USD signal for 30
    minutes, once a week."""
    assert (
        score(EconomicEventCategory.EMPLOYMENT, "ADP Weekly Employment Change")
        is not EconomicEventImportance.CRITICAL
    )


def test_the_monthly_adp_nfp_forecast_stays_critical() -> None:
    """Narrowing the keyword must not cost the monthly release. It
    carries "Non-Farm" in its name, and over-scoring it costs one window
    a month against trading into the real NFP."""
    assert (
        score(EconomicEventCategory.EMPLOYMENT, "ADP Non-Farm Employment Change")
        is EconomicEventImportance.CRITICAL
    )
    assert (
        score(EconomicEventCategory.EMPLOYMENT, "Non-Farm Employment Change")
        is EconomicEventImportance.CRITICAL
    )

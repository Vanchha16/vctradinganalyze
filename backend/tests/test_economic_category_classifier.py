import pytest

from app.models.enums import EconomicEventCategory
from app.services.economic_calendar.category_classifier import classify


@pytest.mark.parametrize(
    ("event_name", "expected"),
    [
        ("FOMC Interest Rate Decision", EconomicEventCategory.CENTRAL_BANK),
        ("ECB Interest Rate Decision", EconomicEventCategory.CENTRAL_BANK),
        ("CPI y/y", EconomicEventCategory.INFLATION),
        ("Core PPI m/m", EconomicEventCategory.INFLATION),
        ("Non-Farm Payrolls", EconomicEventCategory.EMPLOYMENT),
        ("Unemployment Rate", EconomicEventCategory.EMPLOYMENT),
        ("Building Permits", EconomicEventCategory.HOUSING),
        ("Existing Home Sales", EconomicEventCategory.HOUSING),
        ("Consumer Confidence", EconomicEventCategory.CONSUMER),
        ("Consumer Sentiment", EconomicEventCategory.CONSUMER),
        ("Trade Balance", EconomicEventCategory.OTHER),
        ("Current Account", EconomicEventCategory.OTHER),
        ("GDP q/q", EconomicEventCategory.GROWTH),
        ("Retail Sales m/m", EconomicEventCategory.GROWTH),
        ("Industrial Production", EconomicEventCategory.GROWTH),
    ],
)
def test_classify_matches_expected_category(
    event_name: str, expected: EconomicEventCategory
) -> None:
    assert classify(event_name) == expected


def test_classify_prefers_specific_pmi_variants_over_generic_pmi() -> None:
    """docs/14 §3 lists bare "PMI" under Growth but "Manufacturing PMI"/
    "Services PMI" under Other - the specific keyword must win."""
    assert classify("Manufacturing PMI") == EconomicEventCategory.OTHER
    assert classify("Services PMI") == EconomicEventCategory.OTHER
    assert classify("PMI") == EconomicEventCategory.GROWTH


def test_classify_falls_back_to_other_when_no_keyword_matches() -> None:
    assert classify("Some Unrecognized Minor Report") == EconomicEventCategory.OTHER


@pytest.mark.parametrize(
    ("event_name", "expected"),
    [
        # ForexFactory names a rate decision after the rate, not the
        # committee - every one of these classified as OTHER before
        # ADR-150, against a real week of the live feed.
        ("Federal Funds Rate", EconomicEventCategory.CENTRAL_BANK),
        ("Main Refinancing Rate", EconomicEventCategory.CENTRAL_BANK),
        ("Monetary Policy Statement", EconomicEventCategory.CENTRAL_BANK),
        ("Official Bank Rate", EconomicEventCategory.CENTRAL_BANK),
        ("Official Cash Rate", EconomicEventCategory.CENTRAL_BANK),
        ("SNB Policy Rate", EconomicEventCategory.CENTRAL_BANK),
        ("FOMC Meeting Minutes", EconomicEventCategory.CENTRAL_BANK),
        ("Non-Farm Employment Change", EconomicEventCategory.EMPLOYMENT),
        ("ADP Non-Farm Employment Change", EconomicEventCategory.EMPLOYMENT),
        ("Unemployment Claims", EconomicEventCategory.EMPLOYMENT),
        ("Claimant Count Change", EconomicEventCategory.EMPLOYMENT),
        ("Prelim UoM Inflation Expectations", EconomicEventCategory.INFLATION),
    ],
)
def test_classify_recognises_forexfactory_naming(
    event_name: str, expected: EconomicEventCategory
) -> None:
    """ADR-150 - the keyword lists were written against Finnhub's names.
    Adopting ForexFactory without extending them left the ECB and Fed
    rate decisions in OTHER, and therefore scored LOW."""
    assert classify(event_name) == expected

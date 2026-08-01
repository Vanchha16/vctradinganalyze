import pytest

from app.models.enums import EconomicEventCategory
from app.services.economic_calendar.bias_analyzer import analyze
from app.services.economic_calendar.types import MarketBias, SurpriseDirection


def test_inflation_higher_than_forecast_matches_docs_14_example() -> None:
    """docs/14 §7's own worked example: higher CPI -> stronger USD,
    weaker Gold, weaker Equities."""
    bias = analyze(EconomicEventCategory.INFLATION, SurpriseDirection.HIGHER_THAN_FORECAST)
    assert bias == {
        "currency": MarketBias.POTENTIALLY_BULLISH,
        "gold": MarketBias.POTENTIALLY_BEARISH,
        "equities": MarketBias.POTENTIALLY_BEARISH,
    }


def test_inflation_lower_than_forecast_matches_docs_14_example() -> None:
    """docs/14 §7: lower CPI -> weaker USD, stronger Gold, stronger Equities."""
    bias = analyze(EconomicEventCategory.INFLATION, SurpriseDirection.LOWER_THAN_FORECAST)
    assert bias == {
        "currency": MarketBias.POTENTIALLY_BEARISH,
        "gold": MarketBias.POTENTIALLY_BULLISH,
        "equities": MarketBias.POTENTIALLY_BULLISH,
    }


@pytest.mark.parametrize(
    ("category", "direction", "expected"),
    [
        (
            EconomicEventCategory.CENTRAL_BANK,
            SurpriseDirection.HIGHER_THAN_FORECAST,
            {
                "currency": MarketBias.POTENTIALLY_BULLISH,
                "gold": MarketBias.POTENTIALLY_BEARISH,
                "equities": MarketBias.POTENTIALLY_BEARISH,
            },
        ),
        (
            EconomicEventCategory.EMPLOYMENT,
            SurpriseDirection.HIGHER_THAN_FORECAST,
            {
                "currency": MarketBias.POTENTIALLY_BULLISH,
                "gold": MarketBias.POTENTIALLY_BEARISH,
                "equities": MarketBias.POTENTIALLY_BULLISH,
            },
        ),
        (
            EconomicEventCategory.EMPLOYMENT,
            SurpriseDirection.LOWER_THAN_FORECAST,
            {
                "currency": MarketBias.POTENTIALLY_BEARISH,
                "gold": MarketBias.POTENTIALLY_BULLISH,
                "equities": MarketBias.POTENTIALLY_BEARISH,
            },
        ),
        (
            EconomicEventCategory.GROWTH,
            SurpriseDirection.HIGHER_THAN_FORECAST,
            {
                "currency": MarketBias.POTENTIALLY_BULLISH,
                "gold": MarketBias.POTENTIALLY_BEARISH,
                "equities": MarketBias.POTENTIALLY_BULLISH,
            },
        ),
        (
            EconomicEventCategory.CONSUMER,
            SurpriseDirection.HIGHER_THAN_FORECAST,
            {
                "currency": MarketBias.POTENTIALLY_BULLISH,
                "gold": MarketBias.POTENTIALLY_BEARISH,
                "equities": MarketBias.POTENTIALLY_BULLISH,
            },
        ),
        (
            EconomicEventCategory.HOUSING,
            SurpriseDirection.HIGHER_THAN_FORECAST,
            {
                "currency": MarketBias.POTENTIALLY_BULLISH,
                "gold": MarketBias.NEUTRAL,
                "equities": MarketBias.POTENTIALLY_BULLISH,
            },
        ),
        (
            EconomicEventCategory.HOUSING,
            SurpriseDirection.LOWER_THAN_FORECAST,
            {
                "currency": MarketBias.POTENTIALLY_BEARISH,
                "gold": MarketBias.NEUTRAL,
                "equities": MarketBias.POTENTIALLY_BEARISH,
            },
        ),
    ],
)
def test_analyze_matches_docs_47_rule_table(
    category: EconomicEventCategory,
    direction: SurpriseDirection,
    expected: dict[str, MarketBias],
) -> None:
    assert analyze(category, direction) == expected


def test_other_category_is_always_neutral() -> None:
    for direction in SurpriseDirection:
        bias = analyze(EconomicEventCategory.OTHER, direction)
        assert all(value == MarketBias.NEUTRAL for value in bias.values())


def test_in_line_is_always_neutral_regardless_of_category() -> None:
    for category in EconomicEventCategory:
        bias = analyze(category, SurpriseDirection.IN_LINE)
        assert all(value == MarketBias.NEUTRAL for value in bias.values())


def test_analyze_never_returns_a_recommendation_value() -> None:
    """docs/14 §7: "stores the potential impact rather than guaranteeing
    market direction" - only Potentially Bullish/Bearish/Neutral values."""
    for category in EconomicEventCategory:
        for direction in SurpriseDirection:
            bias = analyze(category, direction)
            assert all(isinstance(value, MarketBias) for value in bias.values())

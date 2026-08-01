import pytest

from app.models.enums import NewsCategory
from app.services.news_sentiment.category_classifier import classify
from tests.news_sentiment_helpers import make_raw_article


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("FOMC Holds Rates Steady, Signals Cautious Outlook", NewsCategory.CENTRAL_BANK),
        ("US CPI Rises Above Expectations", NewsCategory.INFLATION),
        ("Non-Farm Payrolls Beat Forecast", NewsCategory.EMPLOYMENT),
        ("Eurozone GDP Growth Slows", NewsCategory.GDP),
        ("Rate Hike Odds Increase Amid Tightening Cycle", NewsCategory.INTEREST_RATES),
        ("Parliament Elects New Government After Election", NewsCategory.POLITICS),
        ("Ceasefire Talks Collapse Amid War", NewsCategory.WAR),
        ("Oil Price Surges on OPEC Supply Cut", NewsCategory.ENERGY),
        ("Gold Price and Silver Price Rally on Bullion Demand", NewsCategory.COMMODITIES),
        ("Bitcoin Rallies Past Key Resistance", NewsCategory.CRYPTO),
        ("Regulator Announces New Compliance Sanction", NewsCategory.REGULATION),
        ("Bank Collapse Triggers Emergency Meeting", NewsCategory.BREAKING_NEWS),
    ],
)
def test_classify_matches_expected_category(title: str, expected: NewsCategory) -> None:
    article = make_raw_article(title=title, summary=None)
    assert classify(article) == expected


def test_classify_falls_back_to_corporate_earnings_when_no_keyword_matches() -> None:
    article = make_raw_article(
        title="Company Reports Quarterly Results In Line With Estimates", summary=None
    )
    assert classify(article) == NewsCategory.CORPORATE_EARNINGS

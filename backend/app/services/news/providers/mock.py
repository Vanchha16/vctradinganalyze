import hashlib
import random
from datetime import datetime, timedelta

from app.services.news.providers.base import NewsProviderCapabilities, RawNewsArticle

_CAPABILITIES = NewsProviderCapabilities(
    supported_languages=frozenset({"en"}),
    max_lookback_days=30,
    supports_push=False,
)

# Deliberately varied across docs/10 §5 categories, source tiers, and
# sentiment polarity, so a single ingestion run exercises every
# downstream analyzer (category_classifier, importance_scorer,
# sentiment_scorer, asset_detector) without needing a real provider.
_TEMPLATE_ARTICLES: list[dict[str, str]] = [
    {
        "title": "US CPI Rises Above Expectations, Fed Rate Hike Odds Increase",
        "summary": "Consumer prices beat forecasts, raising bets on further tightening.",
        "source_name": "Reuters",
    },
    {
        "title": "Non-Farm Payrolls Beat Forecast as Job Market Strengthens",
        "summary": "Employment growth surprised to the upside, unemployment rate falls.",
        "source_name": "Bloomberg",
    },
    {
        "title": "FOMC Holds Rates Steady, Signals Cautious Outlook",
        "summary": "The Federal Reserve left interest rates unchanged, citing balanced risks.",
        "source_name": "Reuters",
    },
    {
        "title": "Gold Prices Slide as Stronger Dollar Weighs on Bullion",
        "summary": "Bullion retreated on rate hike expectations and stronger USD.",
        "source_name": "Forex Factory",
    },
    {
        "title": "Bitcoin Rallies Past Key Resistance as Institutional Demand Grows",
        "summary": "Crypto markets extend gains amid renewed institutional buying.",
        "source_name": "CoinDesk",
    },
    {
        "title": "Eurozone GDP Growth Slows, Recession Fears Resurface",
        "summary": "Growth data missed forecasts, weaker than the previous quarter.",
        "source_name": "Trading Economics",
    },
    {
        "title": "Oil Prices Surge on Escalating Middle East Tensions",
        "summary": "Crude jumped as geopolitical risk premiums widened.",
        "source_name": "Reuters",
    },
    {
        "title": "Retail Sales Beat Expectations, Consumer Confidence Improves",
        "summary": "Stronger-than-forecast retail data lifted sentiment indices.",
        "source_name": "Trading Economics",
    },
    {
        "title": "Company Reports Quarterly Earnings In Line With Estimates",
        "summary": "Corporate earnings matched analyst expectations for the quarter.",
        "source_name": "Bloomberg",
    },
    {
        "title": "Minor Political Reshuffle Draws Limited Market Reaction",
        "summary": "A cabinet change was announced with negligible market impact.",
        "source_name": "Forex Factory",
    },
]

_TEMPLATE_SOURCE_URLS = {
    "Reuters": "https://reuters.com",
    "Bloomberg": "https://bloomberg.com",
    "Forex Factory": "https://forexfactory.com",
    "CoinDesk": "https://coindesk.com",
    "Trading Economics": "https://tradingeconomics.com",
}


def _seed_for(since: datetime) -> int:
    """A stable seed derived from the request window, independent of
    Python's per-process hash randomization - mirrors
    `app.services.market_data.providers.mock._seed_for`, so a given
    `since` always yields the same reproducible article set."""
    digest = hashlib.sha256(since.isoformat().encode()).digest()
    return int.from_bytes(digest[:8], "big")


class MockNewsProvider:
    """Synthetic news generator for Phase 5A (docs/46 §8, ADR-050). Never
    fails, never calls an external service - a real vendor is deferred to
    a follow-up sub-phase once one is chosen."""

    name = "mock"

    def fetch_latest(self, since: datetime) -> list[RawNewsArticle]:
        rng = random.Random(_seed_for(since))
        count = rng.randint(3, len(_TEMPLATE_ARTICLES))
        chosen = rng.sample(_TEMPLATE_ARTICLES, k=count)

        articles: list[RawNewsArticle] = []
        for index, template in enumerate(chosen):
            offset = timedelta(minutes=rng.randint(1, 6 * 60))
            published_at = since + offset
            source_name = template["source_name"]
            slug = template["title"].lower().replace(" ", "-").replace(",", "")[:60]
            url = f"{_TEMPLATE_SOURCE_URLS[source_name]}/article/{slug}-{index}"

            articles.append(
                RawNewsArticle(
                    title=template["title"],
                    url=url,
                    published_at=published_at,
                    source_name=source_name,
                    summary=template["summary"],
                    content=None,
                    language="en",
                )
            )

        return articles

    def health_check(self) -> bool:
        return True

    def capabilities(self) -> NewsProviderCapabilities:
        return _CAPABILITIES

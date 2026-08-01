"""Deterministic category classification (docs/10 §5, docs/46 §5, ADR-055).
Keyword/pattern matching against title + summary text - first matching
category wins, evaluated in a fixed order. No ML/LLM involved."""

from app.models.enums import NewsCategory
from app.services.news.providers.base import RawNewsArticle

# Breaking-news keywords are checked first - an emergency Fed meeting or
# bank collapse is urgent regardless of which other category it would
# otherwise match (docs/10 §11).
_CATEGORY_KEYWORDS: list[tuple[NewsCategory, tuple[str, ...]]] = [
    (
        NewsCategory.BREAKING_NEWS,
        (
            "emergency meeting",
            "bank collapse",
            "flash crash",
            "exchange outage",
            "unexpected rate decision",
            "breaking:",
        ),
    ),
    (
        NewsCategory.CENTRAL_BANK,
        ("fomc", "federal reserve", "fed ", "ecb", "boe", "boj", "rba", "rbnz", "boc", "snb"),
    ),
    (NewsCategory.INFLATION, ("cpi", "inflation", "ppi", "consumer price")),
    (
        NewsCategory.EMPLOYMENT,
        ("non-farm payroll", "nonfarm payroll", "unemployment", "jobless claims", "job market"),
    ),
    (NewsCategory.GDP, ("gdp", "gross domestic product", "economic growth")),
    (
        NewsCategory.INTEREST_RATES,
        ("interest rate", "rate hike", "rate cut", "rates steady", "tightening", "easing"),
    ),
    (NewsCategory.POLITICS, ("election", "political", "parliament", "cabinet", "government")),
    (NewsCategory.WAR, ("war", "military conflict", "invasion", "ceasefire")),
    (
        NewsCategory.ENERGY,
        ("oil price", "crude", "opec", "energy price", "gas price"),
    ),
    (
        NewsCategory.COMMODITIES,
        ("gold price", "silver price", "bullion", "commodity", "commodities"),
    ),
    (NewsCategory.CRYPTO, ("bitcoin", "crypto", "ethereum", "blockchain", "coindesk")),
    (
        NewsCategory.REGULATION,
        ("regulation", "regulator", "sec ", "compliance", "sanction"),
    ),
]

_DEFAULT_CATEGORY = NewsCategory.CORPORATE_EARNINGS


def _article_text(article: RawNewsArticle) -> str:
    return f"{article.title} {article.summary or ''}".lower()


def classify(article: RawNewsArticle) -> NewsCategory:
    text = _article_text(article)
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    return _DEFAULT_CATEGORY

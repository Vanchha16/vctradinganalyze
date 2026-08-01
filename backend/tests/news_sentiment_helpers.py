"""Shared fixtures for News Sentiment Engine tests - mirrors
`tests/smc_helpers.py`'s role for SMC."""

from datetime import UTC, datetime

from app.services.news.providers.base import RawNewsArticle

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_raw_article(
    *,
    title: str = "US CPI Rises Above Expectations, Fed Rate Hike Odds Increase",
    url: str = "https://reuters.com/article/cpi-report",
    published_at: datetime = _BASE,
    source_name: str = "Reuters",
    summary: str | None = "Consumer prices beat forecasts.",
    content: str | None = None,
    language: str = "en",
) -> RawNewsArticle:
    return RawNewsArticle(
        title=title,
        url=url,
        published_at=published_at,
        source_name=source_name,
        summary=summary,
        content=content,
        language=language,
    )

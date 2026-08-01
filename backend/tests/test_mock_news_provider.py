from datetime import UTC, datetime

from app.services.news.providers.mock import MockNewsProvider


def test_fetch_latest_is_deterministic_for_same_since() -> None:
    provider = MockNewsProvider()
    since = datetime(2026, 1, 1, tzinfo=UTC)

    first = provider.fetch_latest(since)
    second = provider.fetch_latest(since)

    assert [a.url for a in first] == [a.url for a in second]
    assert len(first) >= 3


def test_fetch_latest_articles_are_published_after_since() -> None:
    provider = MockNewsProvider()
    since = datetime(2026, 1, 1, tzinfo=UTC)

    articles = provider.fetch_latest(since)

    assert all(article.published_at >= since for article in articles)


def test_health_check_always_true() -> None:
    assert MockNewsProvider().health_check() is True


def test_capabilities_do_not_support_push() -> None:
    capabilities = MockNewsProvider().capabilities()
    assert capabilities.supports_push is False

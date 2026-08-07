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


# --- Cleanup (2026-08-07): URL uniqueness across windows -------------------


def test_fetch_latest_different_since_produces_no_duplicate_urls() -> None:
    """Regression test: a small template pool used to let two different
    `since` windows land the same template at the same list index,
    producing an identical URL - undetected by `dedup_detector` (which
    is window-scoped) and hitting a UNIQUE constraint at the DB layer."""
    provider = MockNewsProvider()

    first_urls = {a.url for a in provider.fetch_latest(datetime(2026, 1, 1, tzinfo=UTC))}
    second_urls = {a.url for a in provider.fetch_latest(datetime(2026, 1, 2, tzinfo=UTC))}

    assert first_urls.isdisjoint(second_urls)


def test_fetch_latest_same_since_produces_identical_urls() -> None:
    """Idempotency must be preserved - the fix must not make the URL
    random or clock-based, only window-derived."""
    provider = MockNewsProvider()
    since = datetime(2026, 1, 1, tzinfo=UTC)

    first_urls = [a.url for a in provider.fetch_latest(since)]
    second_urls = [a.url for a in provider.fetch_latest(since)]

    assert first_urls == second_urls

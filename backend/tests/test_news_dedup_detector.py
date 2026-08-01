from datetime import UTC, datetime, timedelta

from app.models.news_article import NewsArticle
from app.services.news_sentiment.dedup_detector import (
    is_duplicate,
    normalize_url,
    title_similarity,
)
from tests.news_sentiment_helpers import make_raw_article

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _existing(*, title: str, url: str, published_at: datetime = _BASE) -> NewsArticle:
    article = NewsArticle(
        title=title,
        url=url,
        published_at=published_at,
        summary=None,
        content=None,
        language="en",
    )
    return article


def test_normalize_url_strips_tracking_params_and_trailing_slash() -> None:
    a = normalize_url("https://Reuters.com/article/cpi-report/?utm_source=twitter")
    b = normalize_url("https://reuters.com/article/cpi-report")
    assert a == b


def test_title_similarity_identical_titles_is_one() -> None:
    assert title_similarity("US CPI Rises", "US CPI Rises") == 1.0


def test_title_similarity_unrelated_titles_is_low() -> None:
    assert (
        title_similarity("US CPI Rises Above Expectations", "Bitcoin Rallies Past Resistance") < 0.3
    )


def test_is_duplicate_true_for_exact_url_match() -> None:
    candidate = make_raw_article(url="https://reuters.com/a?utm_source=x")
    existing = [_existing(title="Different Headline", url="https://reuters.com/a")]
    assert is_duplicate(candidate, existing) is True


def test_is_duplicate_true_for_similar_title_within_window() -> None:
    candidate = make_raw_article(
        title="US CPI Rises Above Expectations, Fed Rate Hike Odds Increase",
        url="https://bloomberg.com/different-url",
        published_at=_BASE + timedelta(hours=1),
    )
    existing = [
        _existing(
            title="US CPI Rises Above Expectations Fed Rate Hike Odds Increase",
            url="https://reuters.com/a",
            published_at=_BASE,
        )
    ]
    assert is_duplicate(candidate, existing) is True


def test_is_duplicate_false_outside_time_window() -> None:
    candidate = make_raw_article(
        title="US CPI Rises Above Expectations, Fed Rate Hike Odds Increase",
        url="https://bloomberg.com/different-url",
        published_at=_BASE + timedelta(hours=12),
    )
    existing = [
        _existing(
            title="US CPI Rises Above Expectations Fed Rate Hike Odds Increase",
            url="https://reuters.com/a",
            published_at=_BASE,
        )
    ]
    assert is_duplicate(candidate, existing) is False


def test_is_duplicate_false_for_unrelated_article() -> None:
    candidate = make_raw_article(title="Bitcoin Rallies", url="https://coindesk.com/btc")
    existing = [_existing(title="Gold Prices Slide", url="https://forexfactory.com/gold")]
    assert is_duplicate(candidate, existing) is False

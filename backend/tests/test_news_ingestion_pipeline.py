from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.repositories.asset_repository import AssetRepository
from app.repositories.news_article_repository import NewsArticleRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.services.news.providers.base import NewsProvider, NewsProviderCapabilities, RawNewsArticle
from app.services.news.providers.exceptions import (
    AllNewsProvidersFailedError,
    TransientNewsProviderError,
)
from app.services.news.providers.mock import MockNewsProvider
from app.services.news_ingestion_pipeline import NewsIngestionPipeline
from app.services.news_sentiment.ai_summary_generator import AISummaryGenerator

_TABLES = [Asset.__table__, NewsSource.__table__, NewsArticle.__table__, NewsSentiment.__table__]


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def _no_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # AI summary generation is exercised separately (test_news_ai_summary_generator.py);
    # here it must degrade gracefully to None so pipeline tests never hit a real API.
    monkeypatch.setattr(settings, "openai_api_key", "")


_CAPABILITIES = NewsProviderCapabilities(supported_languages=frozenset({"en"}))


class _FailingProvider:
    name = "failing"

    def fetch_latest(self, since: datetime) -> list[RawNewsArticle]:
        raise TransientNewsProviderError("simulated outage")

    def health_check(self) -> bool:
        return False

    def capabilities(self) -> NewsProviderCapabilities:
        return _CAPABILITIES


def _seed_assets(session: Session) -> None:
    session.add_all(
        [
            Asset(
                symbol="EURUSD",
                name="Euro / US Dollar",
                market_type=MarketType.FOREX,
                base_currency="EUR",
                quote_currency="USD",
            ),
            Asset(
                symbol="XAUUSD",
                name="Gold / US Dollar",
                market_type=MarketType.METAL,
                base_currency="XAU",
                quote_currency="USD",
            ),
            Asset(
                symbol="BTCUSD",
                name="Bitcoin / US Dollar",
                market_type=MarketType.CRYPTO,
                base_currency="BTC",
                quote_currency="USD",
            ),
        ]
    )
    session.commit()


def _make_pipeline(
    session: Session, providers: list[NewsProvider] | None = None
) -> NewsIngestionPipeline:
    return NewsIngestionPipeline(
        providers=providers if providers is not None else [MockNewsProvider()],
        source_repository=NewsSourceRepository(session),
        article_repository=NewsArticleRepository(session),
        sentiment_repository=NewsSentimentRepository(session),
        asset_repository=AssetRepository(session),
        ai_summary_generator=AISummaryGenerator(),
    )


def test_run_persists_articles_and_sentiment(session: Session) -> None:
    _seed_assets(session)
    pipeline = _make_pipeline(session)
    since = datetime(2026, 1, 1, tzinfo=UTC)

    result = pipeline.run(since)

    assert result.ingested >= 3
    assert len(result.provider_outcomes) == 1
    assert result.provider_outcomes[0].provider == "mock"
    assert result.provider_outcomes[0].success is True
    articles = session.execute(select(NewsArticle)).scalars().all()
    sentiments = session.execute(select(NewsSentiment)).scalars().all()
    assert len(articles) == result.ingested
    assert len(sentiments) == result.ingested
    for sentiment in sentiments:
        assert sentiment.ai_summary is None  # no OpenAI key configured in this test


def test_run_creates_news_sources_with_known_tiers(session: Session) -> None:
    _seed_assets(session)
    pipeline = _make_pipeline(session)

    pipeline.run(datetime(2026, 1, 1, tzinfo=UTC))

    reuters = session.execute(select(NewsSource).filter_by(name="Reuters")).scalar_one()
    assert reuters.tier.value == "tier_1"


def test_run_twice_with_same_window_does_not_duplicate(session: Session) -> None:
    _seed_assets(session)
    since = datetime(2026, 1, 1, tzinfo=UTC)

    first_pipeline = _make_pipeline(session)
    first_result = first_pipeline.run(since)

    second_pipeline = _make_pipeline(session)
    second_result = second_pipeline.run(since)

    assert second_result.ingested == 0  # MockNewsProvider is deterministic for a given `since`
    articles = session.execute(select(NewsArticle)).scalars().all()
    assert len(articles) == first_result.ingested


def test_run_three_times_with_slightly_different_since_does_not_raise(session: Session) -> None:
    """Cleanup (2026-08-07) regression test: repeated `POST /admin/news`
    calls a few seconds apart each compute `since` as `now -
    lookback_hours`, so back-to-back runs see slightly different,
    heavily overlapping windows - exactly what surfaced the
    `UNIQUE constraint failed: news_articles.url` bug in 9G. Must not
    raise, and must not create more distinct articles than a single run
    would (the same real articles keep getting re-seen and skipped)."""
    _seed_assets(session)
    base = datetime(2026, 1, 1, tzinfo=UTC)

    results = [
        _make_pipeline(session).run(base + timedelta(seconds=offset))
        for offset in (0, 5, 11)
    ]

    articles = session.execute(select(NewsArticle)).scalars().all()
    assert len(articles) == len({a.url for a in articles})  # no duplicate URLs persisted
    assert len(articles) >= results[0].ingested


def test_run_detects_affected_assets(session: Session) -> None:
    _seed_assets(session)
    pipeline = _make_pipeline(session)

    pipeline.run(datetime(2026, 1, 1, tzinfo=UTC))

    sentiments = session.execute(select(NewsSentiment)).scalars().all()
    assert any(sentiment.affected_assets for sentiment in sentiments)


# --- Phase 9G: failure distinguishability (ADR-139) ------------------------


def test_run_raises_when_every_provider_fails(session: Session) -> None:
    """§3/§8's regression test for the actual production defect - a
    total provider failure must not look like a clean, empty success."""
    pipeline = _make_pipeline(session, providers=[_FailingProvider()])

    with pytest.raises(AllNewsProvidersFailedError):
        pipeline.run(datetime(2026, 1, 1, tzinfo=UTC))


def test_run_one_of_two_providers_failing_still_ingests_from_the_other(session: Session) -> None:
    _seed_assets(session)
    pipeline = _make_pipeline(session, providers=[_FailingProvider(), MockNewsProvider()])

    result = pipeline.run(datetime(2026, 1, 1, tzinfo=UTC))

    assert result.ingested > 0
    outcomes_by_provider = {o.provider: o for o in result.provider_outcomes}
    assert outcomes_by_provider["failing"].success is False
    assert outcomes_by_provider["mock"].success is True


def test_provider_names_and_uses_mock() -> None:
    pipeline = NewsIngestionPipeline(
        providers=[MockNewsProvider()],
        source_repository=None,  # type: ignore[arg-type]
        article_repository=None,  # type: ignore[arg-type]
        sentiment_repository=None,  # type: ignore[arg-type]
        asset_repository=None,  # type: ignore[arg-type]
        ai_summary_generator=None,  # type: ignore[arg-type]
    )

    assert pipeline.provider_names == ["mock"]
    assert pipeline.uses_mock is True

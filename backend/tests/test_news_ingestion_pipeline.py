from collections.abc import Generator
from datetime import UTC, datetime

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


def _make_pipeline(session: Session) -> NewsIngestionPipeline:
    return NewsIngestionPipeline(
        providers=[MockNewsProvider()],
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

    ingested = pipeline.run(since)

    assert ingested >= 3
    articles = session.execute(select(NewsArticle)).scalars().all()
    sentiments = session.execute(select(NewsSentiment)).scalars().all()
    assert len(articles) == ingested
    assert len(sentiments) == ingested
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
    first_count = first_pipeline.run(since)

    second_pipeline = _make_pipeline(session)
    second_count = second_pipeline.run(since)

    assert second_count == 0  # MockNewsProvider is deterministic for a given `since`
    articles = session.execute(select(NewsArticle)).scalars().all()
    assert len(articles) == first_count


def test_run_detects_affected_assets(session: Session) -> None:
    _seed_assets(session)
    pipeline = _make_pipeline(session)

    pipeline.run(datetime(2026, 1, 1, tzinfo=UTC))

    sentiments = session.execute(select(NewsSentiment)).scalars().all()
    assert any(sentiment.affected_assets for sentiment in sentiments)

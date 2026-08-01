from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.enums import NewsCategory, NewsImportance, NewsSentimentLabel, NewsSourceTier
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.services.news_sentiment_engine import NewsSentimentEngine

_TABLES = [NewsSource.__table__, NewsArticle.__table__, NewsSentiment.__table__]
_BASE = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _seed_article_with_sentiment(
    session: Session, *, affected_assets: list[str], published_at: datetime
) -> None:
    source = NewsSource(
        name="Reuters", website="https://reuters.com", tier=NewsSourceTier.TIER_1, priority=0
    )
    session.add(source)
    session.flush()

    article = NewsArticle(
        source_id=source.id,
        title="Gold Prices Slide as Stronger Dollar Weighs on Bullion",
        summary="Bullion retreated.",
        url=f"https://reuters.com/{published_at.isoformat()}",
        category=NewsCategory.COMMODITIES,
        language="en",
        importance=NewsImportance.MEDIUM,
        published_at=published_at,
    )
    session.add(article)
    session.flush()

    session.add(
        NewsSentiment(
            article_id=article.id,
            sentiment=NewsSentimentLabel.BEARISH,
            confidence=65.0,
            reason="Matched 1 sentiment keyword(s): slide (score=-1.0).",
            affected_assets=affected_assets,
            ai_summary=None,
        )
    )
    session.commit()


def test_get_sentiment_for_asset_returns_matching_articles(session: Session) -> None:
    _seed_article_with_sentiment(session, affected_assets=["XAUUSD"], published_at=_BASE)
    engine = NewsSentimentEngine(NewsSentimentRepository(session))

    result = engine.get_sentiment_for_asset("XAUUSD", since=_BASE - timedelta(hours=1))

    assert result.symbol == "XAUUSD"
    assert len(result.articles) == 1
    assert result.articles[0].sentiment == NewsSentimentLabel.BEARISH
    assert result.articles[0].source == "Reuters"


def test_get_sentiment_for_asset_excludes_unrelated_assets(session: Session) -> None:
    _seed_article_with_sentiment(session, affected_assets=["EURUSD"], published_at=_BASE)
    engine = NewsSentimentEngine(NewsSentimentRepository(session))

    result = engine.get_sentiment_for_asset("XAUUSD", since=_BASE - timedelta(hours=1))

    assert result.articles == []


def test_get_sentiment_for_asset_excludes_articles_before_since(session: Session) -> None:
    _seed_article_with_sentiment(session, affected_assets=["XAUUSD"], published_at=_BASE)
    engine = NewsSentimentEngine(NewsSentimentRepository(session))

    result = engine.get_sentiment_for_asset("XAUUSD", since=_BASE + timedelta(hours=1))

    assert result.articles == []


def test_get_sentiment_for_asset_no_articles_is_valid_empty_result(session: Session) -> None:
    engine = NewsSentimentEngine(NewsSentimentRepository(session))

    result = engine.get_sentiment_for_asset("XAUUSD", since=_BASE)

    assert result.articles == []
    assert result.warnings == []

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_db
from app.main import app
from app.models.asset import Asset
from app.models.enums import (
    MarketType,
    NewsCategory,
    NewsImportance,
    NewsSentimentLabel,
    NewsSourceTier,
)
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource

_TABLES = [
    Asset.__table__,
    NewsSource.__table__,
    NewsArticle.__table__,
    NewsSentiment.__table__,
]
_BASE = datetime.now(UTC) - timedelta(hours=2)


@pytest.fixture
def session_engine() -> Generator[object, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    yield engine


@pytest.fixture
def client(session_engine: object) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = Session(session_engine)  # type: ignore[arg-type]
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def session(session_engine: object) -> Generator[Session, None, None]:
    with Session(session_engine) as session:  # type: ignore[arg-type]
        yield session


def _seed(session: Session) -> tuple[Asset, NewsArticle]:
    asset = Asset(
        symbol="XAUUSD",
        name="Gold / US Dollar",
        market_type=MarketType.METAL,
        base_currency="XAU",
        quote_currency="USD",
    )
    source = NewsSource(
        name="Reuters", website="https://reuters.com", tier=NewsSourceTier.TIER_1, priority=0
    )
    session.add_all([asset, source])
    session.flush()

    article = NewsArticle(
        source_id=source.id,
        title="Gold Prices Slide as Stronger Dollar Weighs on Bullion",
        summary="Bullion retreated.",
        content=None,
        url="https://reuters.com/gold-slide",
        category=NewsCategory.COMMODITIES,
        language="en",
        importance=NewsImportance.MEDIUM,
        published_at=_BASE,
    )
    session.add(article)
    session.flush()

    session.add(
        NewsSentiment(
            article_id=article.id,
            sentiment=NewsSentimentLabel.BEARISH,
            confidence=65.0,
            reason="Matched 1 sentiment keyword(s): slide (score=-1.0).",
            affected_assets=["XAUUSD"],
            ai_summary=None,
        )
    )
    session.commit()
    session.refresh(article)
    return asset, article


def test_list_news_returns_paginated_articles(client: TestClient, session: Session) -> None:
    _seed(session)

    response = client.get("/api/v1/news")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["source"] == "Reuters"
    assert body["items"][0]["sentiment"] == "bearish"


def test_list_news_filters_by_category(client: TestClient, session: Session) -> None:
    _seed(session)

    response = client.get("/api/v1/news", params={"category": "crypto"})

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_get_news_article_detail(client: TestClient, session: Session) -> None:
    _, article = _seed(session)

    response = client.get(f"/api/v1/news/{article.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["sentiment"]["sentiment"] == "bearish"
    assert body["sentiment"]["affected_assets"] == ["XAUUSD"]


def test_get_news_article_404_for_unknown_id(client: TestClient, session: Session) -> None:
    import uuid

    response = client.get(f"/api/v1/news/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_news_sentiment_for_asset(client: TestClient, session: Session) -> None:
    _seed(session)

    response = client.get("/api/v1/analysis/news/XAUUSD", params={"since": "48h"})

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "XAUUSD"
    assert len(body["articles"]) == 1
    assert body["articles"][0]["sentiment"] == "bearish"


def test_get_news_sentiment_404_for_unknown_asset(client: TestClient, session: Session) -> None:
    response = client.get("/api/v1/analysis/news/NOTREAL")

    assert response.status_code == 404


def test_get_news_sentiment_empty_articles_is_200_not_404(
    client: TestClient, session: Session
) -> None:
    asset = Asset(
        symbol="EURUSD",
        name="Euro / US Dollar",
        market_type=MarketType.FOREX,
        base_currency="EUR",
        quote_currency="USD",
    )
    session.add(asset)
    session.commit()

    response = client.get("/api/v1/analysis/news/EURUSD")

    assert response.status_code == 200
    assert response.json()["articles"] == []


def test_get_news_sentiment_invalid_since_is_422(client: TestClient, session: Session) -> None:
    asset = Asset(
        symbol="EURUSD",
        name="Euro / US Dollar",
        market_type=MarketType.FOREX,
        base_currency="EUR",
        quote_currency="USD",
    )
    session.add(asset)
    session.commit()

    response = client.get("/api/v1/analysis/news/EURUSD", params={"since": "not-a-window"})

    assert response.status_code == 422


def test_news_routes_require_no_authentication(client: TestClient, session: Session) -> None:
    _seed(session)

    response = client.get("/api/v1/news")

    assert response.status_code == 200

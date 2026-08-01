import math
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.dependencies.ai_orchestrator import get_ai_provider
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.economic_event import EconomicEvent
from app.models.enums import MarketType, Timeframe, UserRole
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState
from app.models.user import User
from app.services.ai_orchestrator.providers.mock import MockAIProvider

_TABLES = [
    Asset.__table__,
    PriceCandle.__table__,
    SMCEvent.__table__,
    SMCProcessingState.__table__,
    NewsSource.__table__,
    NewsArticle.__table__,
    NewsSentiment.__table__,
    EconomicEvent.__table__,
    AIAnalysis.__table__,
]

_USER = User(
    id=uuid.uuid4(),
    email="trader@example.com",
    username="trader",
    password_hash="hashed",
    role=UserRole.REGISTERED,
)


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
    app.dependency_overrides[get_current_user] = lambda: _USER
    app.dependency_overrides[get_ai_provider] = lambda: MockAIProvider()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def session(session_engine: object) -> Generator[Session, None, None]:
    with Session(session_engine) as session:  # type: ignore[arg-type]
        yield session


def _make_asset(session: Session) -> Asset:
    asset = Asset(
        symbol="EURUSD",
        name="Euro / US Dollar",
        market_type=MarketType.FOREX,
        base_currency="EUR",
        quote_currency="USD",
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _seed_trending_candles(
    session: Session, asset: Asset, timeframe: Timeframe, count: int
) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(count):
        mid = 100 + 0.3 * i + math.sin(2 * math.pi * i / 24) * 5
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=timeframe,
                timestamp=base + timedelta(hours=i),
                open=Decimal(str(mid)),
                high=Decimal(str(mid + 1)),
                low=Decimal(str(mid - 1)),
                close=Decimal(str(mid)),
                volume=Decimal(str(1000 + i)),
            )
        )
    session.commit()


def test_generate_ai_analysis_requires_authentication(client: TestClient, session: Session) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    _make_asset(session)

    response = client.post("/api/v1/analysis/ai/EURUSD", params={"timeframe": "h1"})

    assert response.status_code in (401, 403)


def test_generate_ai_analysis_returns_structured_response(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300)

    response = client.post("/api/v1/analysis/ai/EURUSD", params={"timeframe": "h1"})

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["recommendation"] in ("buy", "sell", "wait")
    assert body["reasoning"]["summary"] == "Mock summary."


def test_generate_ai_analysis_404_for_unknown_symbol(client: TestClient, session: Session) -> None:
    response = client.post("/api/v1/analysis/ai/NOTREAL", params={"timeframe": "h1"})
    assert response.status_code == 404


def test_get_ai_analysis_by_id_returns_persisted_row(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300)
    created = client.post("/api/v1/analysis/ai/EURUSD", params={"timeframe": "h1"}).json()

    response = client.get(f"/api/v1/analysis/ai/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_ai_analysis_404_for_unknown_id(client: TestClient, session: Session) -> None:
    response = client.get(f"/api/v1/analysis/ai/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_ai_analysis_history_returns_paginated_results(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300)
    client.post("/api/v1/analysis/ai/EURUSD", params={"timeframe": "h1"})
    client.post("/api/v1/analysis/ai/EURUSD", params={"timeframe": "h1"})

    response = client.get("/api/v1/analysis/history", params={"symbol": "EURUSD"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["page"] == 1

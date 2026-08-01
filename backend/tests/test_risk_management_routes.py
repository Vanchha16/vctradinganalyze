import math
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_db
from app.main import app
from app.models.asset import Asset
from app.models.economic_event import EconomicEvent
from app.models.enums import MarketType, Timeframe
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState

_TABLES = [
    Asset.__table__,
    PriceCandle.__table__,
    SMCEvent.__table__,
    SMCProcessingState.__table__,
    NewsSource.__table__,
    NewsArticle.__table__,
    NewsSentiment.__table__,
    EconomicEvent.__table__,
]


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


def test_evaluate_risk_returns_structured_response(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300)

    response = client.post(
        "/api/v1/risk/evaluate",
        json={
            "symbol": "EURUSD",
            "timeframe": "h1",
            "direction": "long",
            "entry_price": "150",
            "stop_loss": "140",
            "take_profit": "180",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["risk_reward"] == pytest.approx(3.0)
    assert set(body["breakdown"].keys()) == {
        "trend_quality",
        "technical",
        "smc",
        "risk",
        "news",
        "economic",
        "total",
    }
    # Evidence + verdict only - no bare trading recommendation field.
    assert "recommendation" not in body


def test_evaluate_risk_rejects_below_minimum_rr(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300)

    response = client.post(
        "/api/v1/risk/evaluate",
        json={
            "symbol": "EURUSD",
            "timeframe": "h1",
            "direction": "long",
            "entry_price": "150",
            "stop_loss": "140",
            "take_profit": "155",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approved"] is False
    assert len(body["rejected_reasons"]) > 0
    assert body["breakdown"]["total"] > 0


def test_evaluate_risk_404_for_unknown_symbol(client: TestClient, session: Session) -> None:
    response = client.post(
        "/api/v1/risk/evaluate",
        json={
            "symbol": "NOTREAL",
            "timeframe": "h1",
            "direction": "long",
            "entry_price": "150",
            "stop_loss": "140",
            "take_profit": "180",
        },
    )

    assert response.status_code == 404


def test_evaluate_risk_accepts_optional_spread(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300)

    response = client.post(
        "/api/v1/risk/evaluate",
        json={
            "symbol": "EURUSD",
            "timeframe": "h1",
            "direction": "short",
            "entry_price": "150",
            "stop_loss": "160",
            "take_profit": "120",
            "spread": "0.01",
        },
    )

    assert response.status_code == 200


def test_evaluate_risk_requires_no_authentication(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300)

    response = client.post(
        "/api/v1/risk/evaluate",
        json={
            "symbol": "EURUSD",
            "timeframe": "h1",
            "direction": "long",
            "entry_price": "150",
            "stop_loss": "140",
            "take_profit": "180",
        },
    )

    assert response.status_code == 200

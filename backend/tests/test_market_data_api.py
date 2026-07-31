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
from app.models.enums import MarketType, Timeframe
from app.models.indicator_result import IndicatorResult
from app.models.price_candle import PriceCandle

_TABLES = [Asset.__table__, PriceCandle.__table__, IndicatorResult.__table__]


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


def _make_asset(session: Session, **overrides: object) -> Asset:
    defaults: dict[str, object] = {
        "symbol": "EURUSD",
        "name": "Euro / US Dollar",
        "market_type": MarketType.FOREX,
        "base_currency": "EUR",
        "quote_currency": "USD",
    }
    defaults.update(overrides)
    asset = Asset(**defaults)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def test_list_assets_returns_paginated_results(client: TestClient, session: Session) -> None:
    _make_asset(session, symbol="EURUSD")
    _make_asset(session, symbol="GBPUSD")

    response = client.get("/api/v1/assets")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["limit"] == 20
    assert {a["symbol"] for a in body["items"]} == {"EURUSD", "GBPUSD"}


def test_list_assets_filters_by_market_type(client: TestClient, session: Session) -> None:
    _make_asset(session, symbol="EURUSD", market_type=MarketType.FOREX)
    _make_asset(
        session,
        symbol="BTCUSD",
        market_type=MarketType.CRYPTO,
        base_currency="BTC",
        quote_currency="USD",
    )

    response = client.get("/api/v1/assets", params={"market_type": "crypto"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "BTCUSD"


def test_list_assets_filters_by_is_active(client: TestClient, session: Session) -> None:
    _make_asset(session, symbol="EURUSD", is_active=True)
    _make_asset(session, symbol="GBPUSD", is_active=False)

    response = client.get("/api/v1/assets", params={"is_active": False})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "GBPUSD"


def test_list_assets_page_beyond_data_returns_empty(client: TestClient, session: Session) -> None:
    _make_asset(session)

    response = client.get("/api/v1/assets", params={"page": 5, "limit": 20})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 1


def test_get_asset_returns_404_for_unknown_symbol(client: TestClient) -> None:
    response = client.get("/api/v1/assets/NOTREAL")

    assert response.status_code == 404
    assert response.json()["error"] == "resource_not_found"


def test_get_asset_symbol_normalization_is_case_insensitive(
    client: TestClient, session: Session
) -> None:
    _make_asset(session, symbol="EURUSD")

    lower = client.get("/api/v1/assets/eurusd")
    upper = client.get("/api/v1/assets/EURUSD")

    assert lower.status_code == 200
    assert upper.status_code == 200
    assert lower.json() == upper.json()


def test_get_latest_candle_returns_most_recent(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(3):
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=base + timedelta(minutes=i),
                open=Decimal("1.1"),
                high=Decimal("1.2"),
                low=Decimal("1.0"),
                close=Decimal("1.15"),
            )
        )
    session.commit()

    response = client.get(f"/api/v1/market/{asset.symbol}/latest", params={"timeframe": "m1"})

    assert response.status_code == 200
    body = response.json()
    assert "spread" not in body  # not fabricated - not part of the data model
    assert body["open"] == "1.10000000"


def test_get_latest_candle_returns_404_when_none_exist(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)

    response = client.get(f"/api/v1/market/{asset.symbol}/latest", params={"timeframe": "m1"})

    assert response.status_code == 404


def test_get_candles_returns_recent_when_no_range_given(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(5):
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=base + timedelta(minutes=i),
                open=Decimal("1.1"),
                high=Decimal("1.2"),
                low=Decimal("1.0"),
                close=Decimal("1.15"),
            )
        )
    session.commit()

    response = client.get(f"/api/v1/market/{asset.symbol}/candles", params={"timeframe": "m1"})

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["timeframe"] == "m1"
    assert len(body["items"]) == 5


def test_get_candles_respects_from_to_and_limit(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(10):
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=base + timedelta(minutes=i),
                open=Decimal("1.1"),
                high=Decimal("1.2"),
                low=Decimal("1.0"),
                close=Decimal("1.15"),
            )
        )
    session.commit()

    response = client.get(
        f"/api/v1/market/{asset.symbol}/candles",
        params={
            "timeframe": "m1",
            "from": base.isoformat(),
            "to": (base + timedelta(minutes=9)).isoformat(),
            "limit": 3,
        },
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 3


def test_get_candles_rejects_invalid_timeframe(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)

    response = client.get(
        f"/api/v1/market/{asset.symbol}/candles", params={"timeframe": "not-a-timeframe"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert "message" in body


def test_get_indicators_returns_raw_values(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    session.add(
        IndicatorResult(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            indicator="rsi_14",
            value=Decimal("55.5"),
        )
    )
    session.commit()

    response = client.get(f"/api/v1/market/{asset.symbol}/indicators", params={"timeframe": "m1"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["indicator"] == "rsi_14"


def test_get_indicators_filters_by_indicator_name(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    session.add_all(
        [
            IndicatorResult(
                asset_id=asset.id, timeframe=Timeframe.M1, indicator="rsi_14", value=Decimal("55")
            ),
            IndicatorResult(
                asset_id=asset.id, timeframe=Timeframe.M1, indicator="macd", value=Decimal("0.5")
            ),
        ]
    )
    session.commit()

    response = client.get(
        f"/api/v1/market/{asset.symbol}/indicators",
        params={"timeframe": "m1", "indicator": "macd"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["indicator"] == "macd"


def test_get_indicators_rejects_unknown_indicator_name(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)

    response = client.get(
        f"/api/v1/market/{asset.symbol}/indicators",
        params={"timeframe": "m1", "indicator": "not_a_real_indicator"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"

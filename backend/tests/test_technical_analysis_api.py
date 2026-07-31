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


def _seed_trending_candles(
    session: Session, asset: Asset, timeframe: Timeframe, count: int, *, direction: int = 1
) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    price = Decimal("100")
    step = Decimal("0.5") * direction
    for i in range(count):
        price += step
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=timeframe,
                timestamp=base + timedelta(minutes=i),
                open=price - Decimal("0.1"),
                high=price + Decimal("0.2"),
                low=price - Decimal("0.3"),
                close=price,
                volume=Decimal(str(1000 + i)),
            )
        )
    session.commit()


def test_get_technical_analysis_returns_structured_result(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.M1, 260, direction=1)

    response = client.get(f"/api/v1/analysis/technical/{asset.symbol}", params={"timeframe": "m1"})

    assert response.status_code == 200
    body = response.json()
    assert body["trend"] == "bullish"
    assert 0 <= body["technical_score"] <= 100
    assert set(body["score_breakdown"].keys()) == {
        "trend",
        "momentum",
        "oscillator",
        "volume",
        "volatility",
        "support_resistance",
        "penalties",
        "total",
    }
    assert "ema_20" in body["indicators"]


def test_get_technical_analysis_case_insensitive_symbol(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.M1, 260, direction=1)

    lower = client.get("/api/v1/analysis/technical/eurusd", params={"timeframe": "m1"})
    upper = client.get("/api/v1/analysis/technical/EURUSD", params={"timeframe": "m1"})

    assert lower.status_code == 200
    assert upper.status_code == 200
    assert lower.json() == upper.json()


def test_get_technical_analysis_returns_404_for_unknown_asset(client: TestClient) -> None:
    response = client.get("/api/v1/analysis/technical/NOTREAL", params={"timeframe": "m1"})

    assert response.status_code == 404
    assert response.json()["error"] == "resource_not_found"


def test_get_technical_analysis_returns_404_when_no_candles(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)

    response = client.get(f"/api/v1/analysis/technical/{asset.symbol}", params={"timeframe": "m1"})

    assert response.status_code == 404


def test_get_technical_analysis_rejects_invalid_timeframe(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)

    response = client.get(
        f"/api/v1/analysis/technical/{asset.symbol}", params={"timeframe": "not-a-timeframe"}
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_get_technical_analysis_requires_no_authentication(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.M1, 260, direction=1)

    response = client.get(f"/api/v1/analysis/technical/{asset.symbol}", params={"timeframe": "m1"})

    assert response.status_code == 200  # no Authorization header supplied


def test_get_multi_timeframe_analysis_returns_combined_verdict(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    for timeframe in (Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15):
        _seed_trending_candles(session, asset, timeframe, 260, direction=1)

    response = client.get(f"/api/v1/analysis/technical/{asset.symbol}/multi-timeframe")

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "bullish_alignment"
    assert len(body["timeframes"]) == 4


def test_get_multi_timeframe_analysis_handles_partial_data(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.D1, 260, direction=1)

    response = client.get(f"/api/v1/analysis/technical/{asset.symbol}/multi-timeframe")

    assert response.status_code == 200
    body = response.json()
    assert len(body["timeframes"]) == 1

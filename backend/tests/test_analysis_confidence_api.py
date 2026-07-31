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
from app.models.enums import MarketType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState

_TABLES = [
    Asset.__table__,
    PriceCandle.__table__,
    SMCEvent.__table__,
    SMCProcessingState.__table__,
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
    session: Session, asset: Asset, timeframe: Timeframe, count: int, *, drift: float = 0.3
) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(count):
        mid = 100 + drift * i + math.sin(2 * math.pi * i / 24) * 5
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


def test_get_confidence_returns_structured_evidence(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)

    response = client.get(f"/api/v1/analysis/confidence/{asset.symbol}", params={"timeframe": "h1"})

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["overall_confidence"] <= 100
    assert body["confidence_level"] in {"very_low", "low", "moderate", "high", "very_high"}
    assert body["conflict_severity"] in {"none", "low", "medium", "high"}
    assert isinstance(body["summary"], str) and body["summary"] != ""
    assert set(body["breakdown"].keys()) == {
        "technical_alignment",
        "smc_alignment",
        "regime_confirmation",
        "cross_engine_agreement",
        "data_completeness",
        "freshness",
        "conflict_penalty",
        "total",
    }
    assert body["technical"] is not None
    assert body["smc"] is not None
    assert body["market_regime"] is not None
    # Evidence only - no trading recommendation fields.
    assert "recommendation" not in body
    assert "signal" not in body


def test_get_confidence_degrades_gracefully_when_no_candles(
    client: TestClient, session: Session
) -> None:
    """Distinct from Market Regime/TA/SMC's 404-on-no-candles behavior -
    Confidence Engine treats missing upstream data as evidence in itself
    (docs/45 §5's graceful-degradation design)."""
    asset = _make_asset(session)

    response = client.get(f"/api/v1/analysis/confidence/{asset.symbol}", params={"timeframe": "h1"})

    assert response.status_code == 200
    body = response.json()
    assert body["confidence_level"] == "very_low"
    assert "technical_analysis_unavailable" in body["missing_data"]
    assert "smc_unavailable" in body["missing_data"]
    assert "market_regime_unavailable" in body["missing_data"]
    assert body["technical"] is None
    assert body["smc"] is None
    assert body["market_regime"] is None


def test_get_confidence_returns_404_for_unknown_asset(client: TestClient) -> None:
    response = client.get("/api/v1/analysis/confidence/NOTREAL", params={"timeframe": "h1"})

    assert response.status_code == 404
    assert response.json()["error"] == "resource_not_found"


def test_get_confidence_case_insensitive_symbol(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)

    lower = client.get("/api/v1/analysis/confidence/eurusd", params={"timeframe": "h1"})
    upper = client.get("/api/v1/analysis/confidence/EURUSD", params={"timeframe": "h1"})

    assert lower.status_code == 200
    assert upper.status_code == 200


def test_get_confidence_rejects_invalid_timeframe(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)

    response = client.get(
        f"/api/v1/analysis/confidence/{asset.symbol}", params={"timeframe": "not-a-timeframe"}
    )

    assert response.status_code == 422


def test_get_confidence_requires_no_authentication(client: TestClient, session: Session) -> None:
    asset = _make_asset(session)
    _seed_trending_candles(session, asset, Timeframe.H1, 300, drift=0.3)

    response = client.get(f"/api/v1/analysis/confidence/{asset.symbol}", params={"timeframe": "h1"})

    assert response.status_code == 200  # no Authorization header supplied


def test_get_confidence_multi_timeframe_returns_combined_verdict(
    client: TestClient, session: Session
) -> None:
    asset = _make_asset(session)
    for timeframe in (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15):
        _seed_trending_candles(session, asset, timeframe, 300, drift=0.3)

    response = client.get(f"/api/v1/analysis/confidence/{asset.symbol}/multi-timeframe")

    assert response.status_code == 200
    body = response.json()
    assert len(body["timeframes"]) == 5
    assert body["verdict"] in {"aligned", "mixed"}

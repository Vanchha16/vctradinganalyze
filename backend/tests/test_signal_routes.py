"""Route tests inject a fake `AIOrchestratorEngine` (overriding
`get_ai_orchestrator_engine`) rather than seeding candles through the
full upstream engine stack - `SignalEngine` is a thin wrapper (ADR-085),
so a canned `AIAnalysisResult` is enough to exercise the persistence/API
surface deterministically, without depending on Risk Management's
approval heuristics ever producing BUY/SELL for synthetic data."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.dependencies.ai_orchestrator import get_ai_orchestrator_engine
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, Recommendation, Timeframe, UserRole
from app.models.signal import Signal
from app.models.signal_bookmark import SignalBookmark
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.services.ai_orchestrator.types import AIAnalysisResult, ReasoningSections

_TABLES = [
    User.__table__,
    TelegramAccount.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    SignalBookmark.__table__,
]

_USER = User(
    id=uuid.uuid4(),
    email="trader@example.com",
    username="trader",
    password_hash="hashed",
    role=UserRole.REGISTERED,
)

_REASONING = ReasoningSections(
    summary="s", technical="t", smc="m", economic="e", news="n", risk="r", conclusion="c"
)


class _FakeAIOrchestratorEngine:
    def __init__(self, recommendation: Recommendation) -> None:
        self._recommendation = recommendation

    def generate(self, asset: Asset, timeframe: Timeframe) -> AIAnalysisResult:
        is_wait = self._recommendation is Recommendation.WAIT
        return AIAnalysisResult(
            id=uuid.uuid4(),
            symbol=asset.symbol,
            timeframe=timeframe,
            recommendation=self._recommendation,
            confidence_score=87.0,
            confidence_level="high",
            risk_level=None if is_wait else "medium",
            entry_price=None if is_wait else Decimal("1.17540"),
            stop_loss=None if is_wait else Decimal("1.17120"),
            take_profit=None if is_wait else Decimal("1.18150"),
            execution_guidance=None if is_wait else "normal",
            reasoning=_REASONING,
            model_name="mock",
            prompt_version="1.0.0",
            ai_available=True,
            calculated_at=datetime.now(UTC),
        )


@pytest.fixture
def session_engine() -> Generator[object, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    yield engine


def _make_client(session_engine: object, recommendation: Recommendation) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        db = Session(session_engine)  # type: ignore[arg-type]
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _USER
    app.dependency_overrides[get_ai_orchestrator_engine] = lambda: _FakeAIOrchestratorEngine(
        recommendation
    )
    return TestClient(app)


@pytest.fixture
def buy_client(session_engine: object) -> Generator[TestClient, None, None]:
    with _make_client(session_engine, Recommendation.BUY) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def wait_client(session_engine: object) -> Generator[TestClient, None, None]:
    with _make_client(session_engine, Recommendation.WAIT) as client:
        yield client
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


def test_generate_signal_requires_authentication(buy_client: TestClient, session: Session) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    _make_asset(session)

    response = buy_client.post("/api/v1/signals/generate/EURUSD", params={"timeframe": "h1"})

    assert response.status_code in (401, 403)


def test_generate_signal_for_buy_persists_and_returns_signal(
    buy_client: TestClient, session: Session
) -> None:
    _make_asset(session)

    response = buy_client.post("/api/v1/signals/generate/EURUSD", params={"timeframe": "h1"})

    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] == "buy"
    assert body["signal"] is not None
    assert body["signal"]["signal_type"] == "buy"
    assert body["signal"]["status"] == "active"
    assert body["signal"]["risk_reward"] == pytest.approx(1.4524, abs=0.01)


def test_generate_signal_for_wait_returns_no_signal(
    wait_client: TestClient, session: Session
) -> None:
    _make_asset(session)

    response = wait_client.post("/api/v1/signals/generate/EURUSD", params={"timeframe": "h1"})

    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] == "wait"
    assert body["signal"] is None


def test_generate_signal_404_for_unknown_symbol(buy_client: TestClient) -> None:
    response = buy_client.post("/api/v1/signals/generate/NOTREAL", params={"timeframe": "h1"})
    assert response.status_code == 404


def test_get_signal_by_id_returns_persisted_row(buy_client: TestClient, session: Session) -> None:
    _make_asset(session)
    created = buy_client.post("/api/v1/signals/generate/EURUSD", params={"timeframe": "h1"}).json()

    response = buy_client.get(f"/api/v1/signals/{created['signal']['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["signal"]["id"]


def test_get_signal_404_for_unknown_id(buy_client: TestClient) -> None:
    response = buy_client.get(f"/api/v1/signals/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_signals_filters_by_symbol_and_paginates(
    buy_client: TestClient, session: Session
) -> None:
    _make_asset(session)
    buy_client.post("/api/v1/signals/generate/EURUSD", params={"timeframe": "h1"})
    buy_client.post("/api/v1/signals/generate/EURUSD", params={"timeframe": "h1"})

    response = buy_client.get("/api/v1/signals", params={"symbol": "EURUSD"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["page"] == 1


def test_bookmark_and_delete_bookmark_round_trip(buy_client: TestClient, session: Session) -> None:
    _make_asset(session)
    created = buy_client.post("/api/v1/signals/generate/EURUSD", params={"timeframe": "h1"}).json()
    signal_id = created["signal"]["id"]

    bookmark_response = buy_client.post("/api/v1/signals/bookmark", json={"signal_id": signal_id})
    assert bookmark_response.status_code == 200
    bookmark = bookmark_response.json()
    assert bookmark["signal_id"] == signal_id

    duplicate_response = buy_client.post("/api/v1/signals/bookmark", json={"signal_id": signal_id})
    assert duplicate_response.status_code == 409

    delete_response = buy_client.delete(f"/api/v1/signals/bookmark/{bookmark['id']}")
    assert delete_response.status_code == 204


def test_bookmark_404_for_unknown_signal(buy_client: TestClient) -> None:
    response = buy_client.post("/api/v1/signals/bookmark", json={"signal_id": str(uuid.uuid4())})
    assert response.status_code == 404

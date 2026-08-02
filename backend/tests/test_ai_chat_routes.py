"""Route tests inject a real `AIChatEngine` wired with a fake
`ContextBuilder` and `MockAIProvider` (overriding `get_ai_chat_engine`
directly) rather than the full upstream engine stack - mirrors
`test_signal_routes.py`'s precedent for a thin orchestration layer."""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.dependencies.ai_chat import get_ai_chat_engine
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.conversation import Conversation
from app.models.enums import MarketType, Timeframe, UserRole
from app.models.message import Message
from app.models.signal import Signal
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.signal_repository import SignalRepository
from app.services.ai_chat_engine import AIChatEngine
from app.services.ai_orchestrator.providers.mock import MockAIProvider
from app.services.ai_orchestrator.types import AnalysisContext
from tests.ai_orchestrator_helpers import make_analysis_context

_TABLES = [
    User.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    Conversation.__table__,
    Message.__table__,
]

_USER = User(
    id=uuid.uuid4(),
    email="trader@example.com",
    username="trader",
    password_hash="hashed",
    role=UserRole.REGISTERED,
)


class _FakeContextBuilder:
    def __init__(self, context: AnalysisContext) -> None:
        self._context = context

    def build(self, asset: Asset, timeframe: Timeframe) -> AnalysisContext:
        return self._context


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

    def override_get_ai_chat_engine() -> AIChatEngine:
        db = Session(session_engine)  # type: ignore[arg-type]
        return AIChatEngine(
            context_builder=_FakeContextBuilder(make_analysis_context()),
            provider=MockAIProvider(chat_response_content="It's currently a BUY."),
            asset_repository=AssetRepository(db),
            ai_analysis_repository=AIAnalysisRepository(db),
            signal_repository=SignalRepository(db),
            message_repository=MessageRepository(db),
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _USER
    app.dependency_overrides[get_ai_chat_engine] = override_get_ai_chat_engine
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


def test_create_conversation_requires_authentication(client: TestClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = client.post("/api/v1/chat/conversations", json={})

    assert response.status_code in (401, 403)


def test_create_conversation_returns_active_conversation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat/conversations", json={"symbol": "EURUSD", "timeframe": "h1"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["current_symbol"] == "EURUSD"
    assert body["title"] is None


def test_send_message_returns_assistant_reply(client: TestClient, session: Session) -> None:
    _make_asset(session)
    conversation_id = client.post("/api/v1/chat/conversations", json={}).json()["id"]

    response = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "Why is this a BUY?", "symbol": "EURUSD", "timeframe": "h1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_message"]["content"] == "Why is this a BUY?"
    assert body["assistant_message"]["content"] == "It's currently a BUY."
    assert body["conversation"]["current_symbol"] == "EURUSD"


def test_send_message_404_for_unknown_conversation(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/chat/conversations/{uuid.uuid4()}/messages",
        json={"content": "Hello"},
    )
    assert response.status_code == 404


def test_send_message_404_for_unknown_symbol(client: TestClient) -> None:
    conversation_id = client.post("/api/v1/chat/conversations", json={}).json()["id"]

    response = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "Analyze it", "symbol": "NOTREAL", "timeframe": "h1"},
    )

    assert response.status_code == 404


def test_get_conversation_returns_messages(client: TestClient, session: Session) -> None:
    _make_asset(session)
    conversation_id = client.post("/api/v1/chat/conversations", json={}).json()["id"]
    client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "What is a Fair Value Gap?"},
    )

    response = client.get(f"/api/v1/chat/conversations/{conversation_id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"


def test_list_conversations_defaults_to_active(client: TestClient) -> None:
    client.post("/api/v1/chat/conversations", json={})
    client.post("/api/v1/chat/conversations", json={})

    response = client.get("/api/v1/chat/conversations")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2


def test_archive_conversation_excludes_it_from_default_list(client: TestClient) -> None:
    conversation_id = client.post("/api/v1/chat/conversations", json={}).json()["id"]

    archive_response = client.post(f"/api/v1/chat/conversations/{conversation_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    list_response = client.get("/api/v1/chat/conversations")
    assert list_response.json()["total"] == 0

    archived_list = client.get("/api/v1/chat/conversations", params={"status": "archived"})
    assert archived_list.json()["total"] == 1


def test_delete_conversation_removes_it(client: TestClient) -> None:
    conversation_id = client.post("/api/v1/chat/conversations", json={}).json()["id"]

    delete_response = client.delete(f"/api/v1/chat/conversations/{conversation_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/chat/conversations/{conversation_id}")
    assert get_response.status_code == 404


def test_cannot_access_another_users_conversation(client: TestClient, session: Session) -> None:
    other_user_conversation = Conversation(user_id=uuid.uuid4())
    session.add(other_user_conversation)
    session.commit()
    session.refresh(other_user_conversation)

    response = client.get(f"/api/v1/chat/conversations/{other_user_conversation.id}")

    assert response.status_code == 404

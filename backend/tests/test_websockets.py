import json
import uuid
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from app.core.redis_pubsub import (
    get_price_channel,
    get_signal_channel,
    publish_event_sync,
)
from app.core.security import create_access_token
from app.core.websocket_manager import (
    authenticate_websocket_token,
)
from app.database.base import Base
from app.dependencies import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

_TABLES = [User.__table__]
_USER_ID = uuid.uuid4()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Seed the test user into SQLite session
    with testing_session_local() as session:
        user = User(
            id=_USER_ID,
            email="ws-tester@example.com",
            username="wstester",
            password_hash="hashed",
            role=UserRole.REGISTERED,
            is_active=True,
        )
        session.add(user)
        session.commit()

    with (
        patch("app.core.websocket_manager.SessionLocal", testing_session_local),
        TestClient(app) as test_client,
    ):
        yield test_client

    app.dependency_overrides.clear()


def test_channel_name_helpers() -> None:
    assert get_price_channel("BTCUSD", "m1") == "prices:BTCUSD:m1"
    assert get_price_channel("eurusd", "H1") == "prices:EURUSD:h1"
    assert get_signal_channel() == "signals:updates"


def test_authenticate_websocket_token_valid(client: TestClient) -> None:
    token = create_access_token(_USER_ID)
    user = authenticate_websocket_token(token)
    assert user is not None
    assert user.id == _USER_ID


def test_authenticate_websocket_token_invalid(client: TestClient) -> None:
    assert authenticate_websocket_token(None) is None
    assert authenticate_websocket_token("invalid.jwt.token") is None


def test_websocket_prices_unauthorized(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws/prices?symbol=BTCUSD&timeframe=m1"):
            pass


def test_websocket_prices_invalid_timeframe(client: TestClient) -> None:
    token = create_access_token(_USER_ID)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/api/v1/ws/prices?symbol=BTCUSD&timeframe=invalid_tf&token={token}"
        ):
            pass


def test_websocket_prices_ping_pong(client: TestClient) -> None:
    token = create_access_token(_USER_ID)
    with client.websocket_connect(
        f"/api/v1/ws/prices?symbol=BTCUSD&timeframe=m1&token={token}"
    ) as websocket:
        websocket.send_text("ping")
        response = websocket.receive_text()
        assert response == "pong"


def test_websocket_signals_ping_pong(client: TestClient) -> None:
    token = create_access_token(_USER_ID)
    with client.websocket_connect(f"/api/v1/ws/signals?token={token}") as websocket:
        websocket.send_text("ping")
        response = websocket.receive_text()
        assert response == "pong"


def test_publish_event_sync_fail_open() -> None:
    # Publishing to a dummy channel returns False if redis fails or passes if connected
    result = publish_event_sync("test_channel", {"test": 123})
    assert isinstance(result, bool)


def _receive_json_with_timeout(
    websocket: WebSocketTestSession, *, timeout: float
) -> dict[str, Any] | None:
    """Like `WebSocketTestSession.receive_json`, but bounded - the plain
    version blocks forever on `anyio`'s memory stream if nothing arrives,
    which would hang the whole suite if the pub/sub wiring this is meant
    to verify were ever broken. Returns `None` on timeout instead of
    raising, so a caller can retry rather than treating one timeout as
    a hard failure."""

    async def _recv() -> Any:
        with anyio.fail_after(timeout):
            return await websocket._send_rx.receive()

    try:
        message = websocket.portal.call(_recv)
    except TimeoutError:
        return None
    return dict(json.loads(message["text"]))


def test_websocket_prices_receives_published_candle_event(client: TestClient) -> None:
    """End-to-end: a Redis publish on the price channel actually reaches a
    connected `/ws/prices` client through `ws_manager`'s listener/broadcast -
    the ping/pong tests above only prove the connection itself works, not
    that Redis pub/sub is wired to it (requires a real Redis; CI provides one,
    see `.github/workflows/ci.yml`)."""
    token = create_access_token(_USER_ID)
    channel = get_price_channel("BTCUSD", "m1")
    payload = {"type": "candle", "symbol": "BTCUSD", "timeframe": "m1", "close": 123.45}

    with client.websocket_connect(
        f"/api/v1/ws/prices?symbol=BTCUSD&timeframe=m1&token={token}"
    ) as websocket:
        # The Redis listener task is created on connect but subscribes
        # asynchronously - retry publishing briefly rather than assuming
        # the subscription is already active the instant connect() returns.
        received = None
        for _ in range(30):
            publish_event_sync(channel, payload)
            received = _receive_json_with_timeout(websocket, timeout=0.1)
            if received is not None:
                break

    assert received == payload


def test_websocket_signals_receives_published_status_change_event(client: TestClient) -> None:
    """Same end-to-end check as above, for `/ws/signals` - a distinct route
    wired to a distinct channel (`get_signal_channel`), not covered by the
    prices test."""
    token = create_access_token(_USER_ID)
    channel = get_signal_channel()
    payload = {"event": "status_changed", "signal_id": str(uuid.uuid4()), "status": "triggered"}

    with client.websocket_connect(f"/api/v1/ws/signals?token={token}") as websocket:
        received = None
        for _ in range(30):
            publish_event_sync(channel, payload)
            received = _receive_json_with_timeout(websocket, timeout=0.1)
            if received is not None:
                break

    assert received == payload

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.base import Base
from app.dependencies import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.models.user_session import UserSession

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    AuditLog.__table__,
]

_REGISTER_PAYLOAD = {
    "email": "trader@example.com",
    "username": "trader",
    "password": "Correct-Horse9",
    "full_name": "Jane Trader",
}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)

    def override_get_db() -> Generator[Session, None, None]:
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _register(client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {**_REGISTER_PAYLOAD, **overrides}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _login(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_register_success(client: TestClient) -> None:
    body = _register(client)

    assert body["email"] == "trader@example.com"
    assert body["username"] == "trader"
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_weak_password(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={**_REGISTER_PAYLOAD, "password": "short"})

    assert response.status_code == 422


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    _register(client)
    response = client.post("/api/v1/auth/register", json={**_REGISTER_PAYLOAD, "username": "other"})

    assert response.status_code == 400
    assert response.json()["error"] == "duplicate_user"


def test_login_success(client: TestClient) -> None:
    _register(client)
    body = _login(client)

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] == settings.jwt_access_expire_minutes * 60


def test_login_rejects_wrong_password(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": _REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_credentials"


def test_refresh_issues_new_access_token(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"] is None
    assert body["expires_in"] == settings.jwt_access_expire_minutes * 60


def test_refresh_rejects_invalid_token(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_refresh_token"


def test_logout_invalidates_refresh_token(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)

    logout_response = client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "trader@example.com"


def test_me_rejects_missing_authorization_header(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_access_token"

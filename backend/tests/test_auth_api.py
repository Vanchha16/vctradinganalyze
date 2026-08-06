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


@pytest.fixture(autouse=True)
def _allow_public_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 8E (docs/59 §9) - `POST /auth/register` is closed by default.
    Every test in this file except the two below uses `_register` purely as
    setup for exercising login/refresh/logout/me, not testing registration
    itself - re-enable the flag for the duration of this file so that setup
    keeps working, matching pre-Phase-8E behavior."""
    monkeypatch.setattr(settings, "allow_public_registration", True)


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
        test_client.engine = engine  # type: ignore[attr-defined]
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


def test_register_returns_403_when_public_registration_disabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual default behavior (Phase 8E, docs/59 §9, ADR-119) - every
    other test in this file opts back into the pre-Phase-8E behavior via
    the autouse fixture above; this one explicitly tests the real default."""
    monkeypatch.setattr(settings, "allow_public_registration", False)

    response = client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)

    assert response.status_code == 403
    assert response.json()["error"] == "registration_disabled"


def test_register_disabled_response_does_not_create_a_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allow_public_registration", False)
    client.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": _REGISTER_PAYLOAD["email"], "password": _REGISTER_PAYLOAD["password"]},
    )

    assert login_response.status_code == 401


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


# --- Phase 9B (ADR-133): get_current_user active/deleted enforcement -------


def _disable_user(client: TestClient, *, deleted: bool = False) -> None:
    """Mutate the already-registered `trader@example.com` row directly,
    bypassing the API - simulates an admin disabling/deleting a user whose
    already-issued access token is still live (the exact scenario Item A
    closes)."""
    from datetime import UTC, datetime

    with Session(client.engine) as session:  # type: ignore[attr-defined]
        user = session.query(User).filter_by(email="trader@example.com").one()
        user.is_active = False
        if deleted:
            user.deleted_at = datetime.now(UTC)
        session.commit()


def test_me_rejects_token_for_now_disabled_user(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)
    _disable_user(client)

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 401
    assert response.json()["error"] == "inactive_account"


def test_me_rejects_token_for_now_soft_deleted_user(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)
    _disable_user(client, deleted=True)

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 401
    assert response.json()["error"] == "inactive_account"


def test_me_allows_token_for_still_active_user(client: TestClient) -> None:
    """Control case: an active user's token keeps working - Item A only
    narrows the disabled/deleted path, nothing else."""
    _register(client)
    tokens = _login(client)

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200

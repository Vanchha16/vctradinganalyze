"""API-level tests for Phase 8C (docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md §6.2).

Mirrors `test_signal_routes.py`'s pattern: a real `TestClient` against the
actual app/router, `get_current_user` overridden per test to simulate
different actor roles, and a shared in-memory SQLite database so admin
mutations and `POST /auth/login` can be exercised in the same test (e.g.
"a soft-deleted user cannot log in").
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.models.user_session import UserSession

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    AuditLog.__table__,
]

_PASSWORD = "Correct-Horse9"


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    return engine


@pytest.fixture
def client(engine) -> Generator[TestClient, None, None]:
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


def _make_user(engine, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": "user@example.com",
        "username": "user",
        "password_hash": hash_password(_PASSWORD),
        "role": UserRole.REGISTERED,
    }
    defaults.update(overrides)
    with Session(engine) as session:
        user = User(**defaults)
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _act_as(client: TestClient, actor: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: actor


def _clear_actor(client: TestClient) -> None:
    client.app.dependency_overrides.pop(get_current_user, None)


# --- Authorization -----------------------------------------------------


def test_list_users_rejects_non_admin(client: TestClient, engine) -> None:
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 403
    assert response.json()["error"] == "insufficient_role"


def test_list_users_rejects_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/v1/admin/users")

    assert response.status_code == 401


def test_list_users_allows_admin(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "admin@example.com"


# --- List / search / filter / pagination --------------------------------


def test_list_users_search_and_filter(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_user(engine, email="alice@example.com", username="alice", role=UserRole.PREMIUM)
    _make_user(engine, email="bob@example.com", username="bob", role=UserRole.REGISTERED)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/users", params={"role": "premium"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "alice"

    response = client.get("/api/v1/admin/users", params={"search": "bob"})
    assert response.json()["total"] == 1


def test_list_users_pagination(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    for i in range(5):
        _make_user(engine, email=f"u{i}@example.com", username=f"u{i}")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/users", params={"page": 1, "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 6
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) == 2


def test_list_users_include_deleted_rejected_for_plain_admin(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/users", params={"include_deleted": True})

    assert response.status_code == 403


# --- Create --------------------------------------------------------------


def test_create_user_as_admin_returns_temporary_password(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post(
        "/api/v1/admin/users",
        json={"email": "new@example.com", "username": "newuser", "role": "registered"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["temporary_password"]
    assert body["must_change_password"] is True
    assert body["created_by_admin_id"] == str(admin.id)


def test_create_user_rejects_duplicate_email(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_user(engine, email="taken@example.com", username="taken")
    _act_as(client, admin)

    response = client.post(
        "/api/v1/admin/users",
        json={"email": "taken@example.com", "username": "newname", "role": "registered"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "duplicate_user"


def test_create_user_admin_cannot_grant_admin_role(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post(
        "/api/v1/admin/users",
        json={"email": "new-admin@example.com", "username": "newadmin", "role": "admin"},
    )

    assert response.status_code == 403


def test_create_user_super_admin_can_grant_admin_role(client: TestClient, engine) -> None:
    super_admin = _make_user(
        engine, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    _act_as(client, super_admin)

    response = client.post(
        "/api/v1/admin/users",
        json={"email": "new-admin@example.com", "username": "newadmin", "role": "admin"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "admin"


# --- Detail / Update -------------------------------------------------------


def test_get_user_detail_returns_active_session_count(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    response = client.get(f"/api/v1/admin/users/{target.id}")

    assert response.status_code == 200
    assert response.json()["active_session_count"] == 0


def test_get_user_detail_404_for_unknown_user(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/users/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_update_user_changes_full_name(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    response = client.patch(f"/api/v1/admin/users/{target.id}", json={"full_name": "New Name"})

    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"


def test_update_user_ignores_unknown_fields_like_role(client: TestClient, engine) -> None:
    """Mass-assignment guard (docs/59 §11) - `role`/`is_active`/`password`
    aren't fields on `AdminUserUpdateRequest` at all, so sending them is a
    no-op, not a privilege escalation."""
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}", json={"full_name": "OK", "role": "super_admin"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "registered"


# --- Status / Delete / soft-delete blocks login -----------------------------


def test_disable_user_then_login_fails(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    response = client.patch(f"/api/v1/admin/users/{target.id}/status", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    _clear_actor(client)
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "target@example.com", "password": _PASSWORD}
    )
    assert login_response.status_code == 401
    assert login_response.json()["error"] == "inactive_account"


def test_delete_user_soft_deletes_then_login_fails(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    response = client.delete(f"/api/v1/admin/users/{target.id}")
    assert response.status_code == 204

    _clear_actor(client)
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "target@example.com", "password": _PASSWORD}
    )
    assert login_response.status_code == 401
    assert login_response.json()["error"] == "inactive_account"


def test_delete_user_blocks_self_delete(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.delete(f"/api/v1/admin/users/{admin.id}")

    assert response.status_code == 409


def test_deleted_user_no_longer_appears_in_default_list(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    client.delete(f"/api/v1/admin/users/{target.id}")

    response = client.get("/api/v1/admin/users")
    emails = {item["email"] for item in response.json()["items"]}
    assert "target@example.com" not in emails


# --- Reset password --------------------------------------------------------


def test_reset_password_allows_login_with_new_password(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    response = client.post(f"/api/v1/admin/users/{target.id}/reset-password")
    assert response.status_code == 200
    new_password = response.json()["temporary_password"]

    _clear_actor(client)
    old_login = client.post(
        "/api/v1/auth/login", json={"email": "target@example.com", "password": _PASSWORD}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login", json={"email": "target@example.com", "password": new_password}
    )
    assert new_login.status_code == 200


# --- Role change -------------------------------------------------------------


def test_change_role_rejects_plain_admin(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    response = client.patch(f"/api/v1/admin/users/{target.id}/role", json={"role": "premium"})

    assert response.status_code == 403


def test_change_role_allows_super_admin(client: TestClient, engine) -> None:
    super_admin = _make_user(
        engine, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, super_admin)

    response = client.patch(f"/api/v1/admin/users/{target.id}/role", json={"role": "premium"})

    assert response.status_code == 200
    assert response.json()["role"] == "premium"


def test_change_role_blocks_demoting_last_super_admin(client: TestClient, engine) -> None:
    super_admin = _make_user(
        engine, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    _act_as(client, super_admin)

    response = client.patch(f"/api/v1/admin/users/{super_admin.id}/role", json={"role": "admin"})

    assert response.status_code == 409


# --- Audit logging -----------------------------------------------------------


def test_admin_actions_write_audit_log_entries(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(engine, email="target@example.com", username="target")
    _act_as(client, admin)

    client.post(
        "/api/v1/admin/users",
        json={"email": "created@example.com", "username": "created", "role": "registered"},
    )
    client.patch(f"/api/v1/admin/users/{target.id}", json={"full_name": "Renamed"})
    client.patch(f"/api/v1/admin/users/{target.id}/status", json={"is_active": False})
    client.post(f"/api/v1/admin/users/{target.id}/reset-password")
    client.delete(f"/api/v1/admin/users/{target.id}")

    with Session(engine) as session:
        actions = set(session.execute(select(AuditLog.action)).scalars().all())

    assert actions == {
        "admin_user_created",
        "admin_user_updated",
        "admin_user_disabled",
        "admin_password_reset",
        "admin_user_deleted",
    }

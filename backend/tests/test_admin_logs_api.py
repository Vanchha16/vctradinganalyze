"""API-level tests for Phase 8F (docs/59 §11, ADR-129). Mirrors
`test_admin_users_api.py`'s pattern: a real `TestClient` against the
actual app/router, `get_current_user` overridden per test to simulate
different actor roles, and a shared in-memory SQLite database."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User

_TABLES = [User.__table__, AuditLog.__table__]

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


def _make_log(engine, **overrides: object) -> AuditLog:
    defaults: dict[str, object] = {
        "user_id": None,
        "action": "login_success",
        "resource": "user",
        "resource_id": None,
        "ip_address": None,
        "context": None,
    }
    defaults.update(overrides)
    with Session(engine) as session:
        log = AuditLog(**defaults)
        session.add(log)
        session.commit()
        session.refresh(log)
        session.expunge(log)
        return log


def _act_as(client: TestClient, actor: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: actor


# --- Authorization -----------------------------------------------------


def test_list_logs_rejects_non_admin(client: TestClient, engine) -> None:
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = client.get("/api/v1/admin/logs")

    assert response.status_code == 403
    assert response.json()["error"] == "insufficient_role"


def test_list_logs_rejects_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/v1/admin/logs")

    assert response.status_code == 401


def test_admin_logs_route_has_no_mutation_or_deletion(client: TestClient) -> None:
    """docs/59 §11/ADR-129 - audit logs are read-only via this API. Checks
    the actual OpenAPI schema (routes are lazily included onto `app.routes`
    in this FastAPI version, so inspecting `app.routes` directly misses
    them) rather than just "no test hits them," so a future accidental
    `POST`/`PATCH`/`DELETE /admin/logs*` route would fail this test."""
    schema = client.get("/api/v1/openapi.json").json()
    logs_paths = {
        path: ops for path, ops in schema["paths"].items() if path.startswith("/api/v1/admin/logs")
    }

    assert logs_paths, "expected at least one /admin/logs path in the OpenAPI schema"
    for path, operations in logs_paths.items():
        assert set(operations.keys()) <= {"get"}, f"{path} allows {set(operations.keys())}"


# --- Listing / ordering / filtering / pagination ------------------------


def test_list_logs_returns_newest_first(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    now = datetime.now(UTC)
    old = _make_log(engine, action="login_success", created_at=now - timedelta(hours=2))
    new = _make_log(engine, action="login_success", created_at=now)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/logs")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(new.id), str(old.id)]


def test_list_logs_filters_by_user_id(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    alice = _make_user(engine, email="alice@example.com", username="alice")
    _make_log(engine, user_id=admin.id, action="login_success")
    matching = _make_log(engine, user_id=alice.id, action="login_success")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/logs", params={"user_id": str(alice.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(matching.id)


def test_list_logs_filters_by_action(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_log(engine, action="login_success")
    matching = _make_log(engine, action="admin_role_changed")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/logs", params={"action": "admin_role_changed"})

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(matching.id)


def test_list_logs_filters_by_resource(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_log(engine, resource="user_session", action="logout")
    matching = _make_log(engine, resource="user", action="admin_user_deleted")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/logs", params={"resource": "user"})

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(matching.id)


def test_list_logs_filters_by_date_range(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    now = datetime.now(UTC)
    _make_log(engine, action="login_success", created_at=now - timedelta(days=5))
    matching = _make_log(engine, action="login_success", created_at=now - timedelta(hours=1))
    _act_as(client, admin)

    response = client.get(
        "/api/v1/admin/logs",
        params={
            "from": (now - timedelta(days=1)).isoformat(),
            "to": now.isoformat(),
        },
    )

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(matching.id)


def test_list_logs_combines_filters(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    alice = _make_user(engine, email="alice@example.com", username="alice")
    _make_log(engine, user_id=alice.id, action="login_success", resource="user")
    matching = _make_log(engine, user_id=alice.id, action="login_failed", resource="user")
    _make_log(engine, user_id=admin.id, action="login_failed", resource="user")
    _act_as(client, admin)

    response = client.get(
        "/api/v1/admin/logs", params={"user_id": str(alice.id), "action": "login_failed"}
    )

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(matching.id)


def test_list_logs_pagination(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    for _ in range(5):
        _make_log(engine, action="login_success")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/logs", params={"page": 1, "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) == 2

    page_two = client.get("/api/v1/admin/logs", params={"page": 2, "limit": 2})
    assert len(page_two.json()["items"]) == 2
    assert {item["id"] for item in page_two.json()["items"]}.isdisjoint(
        {item["id"] for item in body["items"]}
    )


# --- Null actor ----------------------------------------------------------


def test_list_logs_serializes_null_actor_without_error(client: TestClient, engine) -> None:
    """A log row can have no actor at all (a failed login before the user
    resolved) or a since-deleted one (`ON DELETE SET NULL`) - both leave
    `user_id=NULL`. The API must render this, not crash (§2 of the spec)."""
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    orphan = _make_log(engine, user_id=None, action="login_failed", resource="user")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/logs")

    assert response.status_code == 200
    row = next(item for item in response.json()["items"] if item["id"] == str(orphan.id))
    assert row["user_id"] is None
    assert row["actor_email"] is None
    assert row["actor_username"] is None


def test_list_logs_resolves_actor_email_and_username(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    alice = _make_user(engine, email="alice@example.com", username="alice")
    log = _make_log(engine, user_id=alice.id, action="login_success")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/logs")

    row = next(item for item in response.json()["items"] if item["id"] == str(log.id))
    assert row["actor_email"] == "alice@example.com"
    assert row["actor_username"] == "alice"

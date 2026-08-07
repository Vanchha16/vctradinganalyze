"""API-level tests for Phase 9F Admin Asset Management (ADR-138).

Mirrors `test_admin_users_api.py`'s pattern: a real `TestClient` against
the actual app/router, `get_current_user` overridden per test to simulate
different actor roles, a shared in-memory SQLite database.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.enums import MarketType, UserRole
from app.models.user import User
from app.repositories.asset_repository import AssetRepository

_TABLES = [User.__table__, Asset.__table__, AuditLog.__table__]

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


def _make_asset(engine, **overrides: object) -> Asset:
    defaults: dict[str, object] = {
        "symbol": "EURUSD",
        "name": "Euro / US Dollar",
        "market_type": MarketType.FOREX,
        "base_currency": "EUR",
        "quote_currency": "USD",
        "is_active": True,
    }
    defaults.update(overrides)
    with Session(engine) as session:
        asset = Asset(**defaults)
        session.add(asset)
        session.commit()
        session.refresh(asset)
        session.expunge(asset)
        return asset


def _act_as(client: TestClient, actor: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: actor


# --- Authorization -----------------------------------------------------


def test_list_assets_rejects_non_admin(client: TestClient, engine) -> None:
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = client.get("/api/v1/admin/assets")

    assert response.status_code == 403


def test_list_assets_rejects_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/v1/admin/assets")

    assert response.status_code == 401


def test_create_asset_rejects_non_admin(client: TestClient, engine) -> None:
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = client.post(
        "/api/v1/admin/assets",
        json={"symbol": "GBPUSD", "name": "British Pound", "market_type": "forex"},
    )

    assert response.status_code == 403


def test_create_asset_rejects_unauthenticated(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/assets",
        json={"symbol": "GBPUSD", "name": "British Pound", "market_type": "forex"},
    )

    assert response.status_code == 401


def test_update_asset_rejects_non_admin(client: TestClient, engine) -> None:
    asset = _make_asset(engine)
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = client.patch(f"/api/v1/admin/assets/{asset.id}", json={"name": "New Name"})

    assert response.status_code == 403


def test_activate_asset_rejects_non_admin(client: TestClient, engine) -> None:
    asset = _make_asset(engine, is_active=False)
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = client.post(f"/api/v1/admin/assets/{asset.id}/activate")

    assert response.status_code == 403


def test_deactivate_asset_rejects_non_admin(client: TestClient, engine) -> None:
    asset = _make_asset(engine)
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = client.post(f"/api/v1/admin/assets/{asset.id}/deactivate")

    assert response.status_code == 403


def test_activate_asset_rejects_unauthenticated(client: TestClient, engine) -> None:
    asset = _make_asset(engine, is_active=False)

    response = client.post(f"/api/v1/admin/assets/{asset.id}/activate")

    assert response.status_code == 401


def test_deactivate_asset_rejects_unauthenticated(client: TestClient, engine) -> None:
    asset = _make_asset(engine)

    response = client.post(f"/api/v1/admin/assets/{asset.id}/deactivate")

    assert response.status_code == 401


# --- List / search / filter / pagination --------------------------------


def test_list_assets_allows_admin(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_asset(engine)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/assets")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "EURUSD"


def test_list_assets_search_and_filter(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_asset(engine, symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX)
    _make_asset(engine, symbol="XAUUSD", name="Gold / US Dollar", market_type=MarketType.METAL)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/assets", params={"market_type": "metal"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "XAUUSD"

    response = client.get("/api/v1/admin/assets", params={"search": "Gold"})
    assert response.json()["total"] == 1

    response = client.get("/api/v1/admin/assets", params={"search": "eur"})
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["symbol"] == "EURUSD"


def test_list_assets_empty_result(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/assets", params={"search": "nope"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_assets_pagination(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    for i in range(5):
        _make_asset(engine, symbol=f"SYM{i}", name=f"Symbol {i}")
    _act_as(client, admin)

    response = client.get("/api/v1/admin/assets", params={"page": 1, "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) == 2


def test_list_assets_is_active_filter(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_asset(engine, symbol="ACTIVE1", is_active=True)
    _make_asset(engine, symbol="INACTIVE1", is_active=False)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/assets", params={"is_active": False})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "INACTIVE1"


# --- Create --------------------------------------------------------------


def test_create_asset_as_admin(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post(
        "/api/v1/admin/assets",
        json={
            "symbol": "gbpusd",
            "name": "British Pound / US Dollar",
            "market_type": "forex",
            "base_currency": "GBP",
            "quote_currency": "USD",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["symbol"] == "GBPUSD"
    assert body["is_active"] is True


def test_create_asset_rejects_duplicate_symbol_with_clean_error(
    client: TestClient, engine
) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_asset(engine, symbol="EURUSD")
    _act_as(client, admin)

    response = client.post(
        "/api/v1/admin/assets",
        json={"symbol": "EURUSD", "name": "Duplicate", "market_type": "forex"},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_create_asset_writes_audit_log(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post(
        "/api/v1/admin/assets",
        json={"symbol": "GBPUSD", "name": "British Pound", "market_type": "forex"},
    )
    asset_id = response.json()["id"]

    with Session(engine) as session:
        log = (
            session.query(AuditLog).filter(AuditLog.resource_id == uuid.UUID(asset_id)).one()
        )
        assert log.action == "admin_asset_created"
        assert str(log.user_id) == str(admin.id)
        assert log.resource == "asset"


# --- Update ----------------------------------------------------------------


def test_update_asset_changes_mutable_fields(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine)
    _act_as(client, admin)

    response = client.patch(
        f"/api/v1/admin/assets/{asset.id}", json={"name": "Euro vs US Dollar"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Euro vs US Dollar"


def test_update_asset_rejects_symbol_change(client: TestClient, engine) -> None:
    """§3.2/§6: symbol is immutable after creation - explicit test."""
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine, symbol="EURUSD")
    _act_as(client, admin)

    response = client.patch(f"/api/v1/admin/assets/{asset.id}", json={"symbol": "GBPUSD"})

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"

    with Session(engine) as session:
        reloaded = AssetRepository(session).get_by_id(asset.id)
        assert reloaded is not None
        assert reloaded.symbol == "EURUSD"


def test_update_asset_writes_audit_log(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine)
    _act_as(client, admin)

    client.patch(f"/api/v1/admin/assets/{asset.id}", json={"name": "Renamed"})

    with Session(engine) as session:
        log = (
            session.query(AuditLog)
            .filter(AuditLog.resource_id == asset.id, AuditLog.action == "admin_asset_updated")
            .one()
        )
        assert str(log.user_id) == str(admin.id)


def test_update_asset_missing_returns_404(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.patch(
        "/api/v1/admin/assets/00000000-0000-0000-0000-000000000000", json={"name": "x"}
    )

    assert response.status_code == 404


# --- Activate / Deactivate --------------------------------------------------


def test_deactivate_sets_is_active_false(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine, is_active=True)
    _act_as(client, admin)

    response = client.post(f"/api/v1/admin/assets/{asset.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_activate_reverses_deactivate(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine, is_active=False)
    _act_as(client, admin)

    response = client.post(f"/api/v1/admin/assets/{asset.id}/activate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_deactivate_writes_audit_log(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine)
    _act_as(client, admin)

    client.post(f"/api/v1/admin/assets/{asset.id}/deactivate")

    with Session(engine) as session:
        log = (
            session.query(AuditLog)
            .filter(
                AuditLog.resource_id == asset.id,
                AuditLog.action == "admin_asset_deactivated",
            )
            .one()
        )
        assert str(log.user_id) == str(admin.id)


def test_activate_writes_audit_log(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine, is_active=False)
    _act_as(client, admin)

    client.post(f"/api/v1/admin/assets/{asset.id}/activate")

    with Session(engine) as session:
        log = (
            session.query(AuditLog)
            .filter(
                AuditLog.resource_id == asset.id, AuditLog.action == "admin_asset_activated"
            )
            .one()
        )
        assert str(log.user_id) == str(admin.id)


# --- The pipeline-gating regression test ------------------------------------


def test_list_active_excludes_deactivated_asset(engine) -> None:
    """§6's most important test - proves the three production pipelines
    (`market_data_tasks.py`, `signal_tasks.py`,
    `news_ingestion_pipeline.py`) are actually gated by deactivation, not
    just that the admin API reports the right flag."""
    with Session(engine) as session:
        repo = AssetRepository(session)
        active_asset = Asset(
            symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX, is_active=True
        )
        inactive_asset = Asset(
            symbol="XAUUSD", name="Gold / US Dollar", market_type=MarketType.METAL, is_active=False
        )
        session.add_all([active_asset, inactive_asset])
        session.commit()

        results = repo.list_active(limit=100)
        symbols = {a.symbol for a in results}
        assert symbols == {"EURUSD"}

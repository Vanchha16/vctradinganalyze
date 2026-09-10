"""Admin credential management (ADR-156).

The tests that matter most here are the negative ones: that a stored key
never comes back out, that a plain admin cannot write one, and that the
plaintext never reaches the audit log.
"""

import uuid
from collections.abc import Generator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.base import Base
from app.dependencies import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.api_credential import ApiCredential
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.services import credential_resolver

_TABLES = [User.__table__, ApiCredential.__table__, AuditLog.__table__]

_REAL_KEY = "super-secret-vendor-key-abcd1234"


@pytest.fixture
def session_engine() -> Generator[object, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    yield engine


@pytest.fixture
def db(session_engine: object) -> Generator[Session, None, None]:
    with Session(session_engine) as session:  # type: ignore[arg-type]
        yield session


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "credential_encryption_key", Fernet.generate_key().decode())
    credential_resolver.invalidate()


def _user(db: Session, role: UserRole, username: str) -> User:
    user = User(
        email=f"{username}@example.com",
        username=username,
        password_hash="x",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def client(session_engine: object, db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        s = Session(session_engine)  # type: ignore[arg-type]
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def test_super_admin_can_store_a_key(client: TestClient, db: Session) -> None:
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))

    response = client.put("/api/v1/admin/credentials/openai", json={"value": _REAL_KEY})

    assert response.status_code == 200
    body = response.json()
    assert body["is_set"] is True
    assert body["source"] == "database"


def test_the_stored_value_is_never_returned(client: TestClient, db: Session) -> None:
    """The single most important property of this feature: a key travels
    one way, operator -> vendor. Any route handing it back is a route an
    attacker can use too."""
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))
    client.put("/api/v1/admin/credentials/openai", json={"value": _REAL_KEY})

    listed = client.get("/api/v1/admin/credentials")

    assert listed.status_code == 200
    assert _REAL_KEY not in listed.text
    # Only the tail is disclosed - enough to tell two keys apart.
    openai = next(i for i in listed.json()["items"] if i["name"] == "openai")
    assert openai["hint"] == "1234"


def test_the_value_is_encrypted_at_rest(client: TestClient, db: Session) -> None:
    """`~/deploy_backups` accumulates a gzipped dump per deploy, so a
    plaintext column would put live keys in files on disk."""
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))
    client.put("/api/v1/admin/credentials/openai", json={"value": _REAL_KEY})

    stored = db.query(ApiCredential).filter_by(name="openai").one()

    assert _REAL_KEY not in stored.encrypted_value
    assert stored.encrypted_value.startswith("gAAAAA")  # Fernet token prefix


def test_the_plaintext_never_reaches_the_audit_log(client: TestClient, db: Session) -> None:
    """An audit trail recording the value would put every rotated key
    permanently in a table the admin UI can read."""
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))
    client.put("/api/v1/admin/credentials/openai", json={"value": _REAL_KEY})

    entries = db.query(AuditLog).all()

    assert len(entries) == 1
    assert entries[0].action == "admin_credential_created"
    assert _REAL_KEY not in str(entries[0].context)
    assert entries[0].context is not None
    assert entries[0].context["hint"] == "1234"


def test_a_plain_admin_cannot_write_a_credential(client: TestClient, db: Session) -> None:
    """Super-admin only, matching the precedent that role changes are.
    A web form that writes credentials raises the blast radius of a
    compromised admin account."""
    _as(_user(db, UserRole.ADMIN, "admin"))

    assert (
        client.put("/api/v1/admin/credentials/openai", json={"value": _REAL_KEY}).status_code == 403
    )
    assert client.get("/api/v1/admin/credentials").status_code == 403


def test_a_registered_user_cannot_reach_it_at_all(client: TestClient, db: Session) -> None:
    _as(_user(db, UserRole.REGISTERED, "trader"))

    assert client.get("/api/v1/admin/credentials").status_code == 403


def test_an_unknown_credential_name_is_404_not_a_new_row(
    client: TestClient, db: Session
) -> None:
    """This table is a fixed list of integrations, not an arbitrary
    key/value store."""
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))

    response = client.put("/api/v1/admin/credentials/whatever", json={"value": _REAL_KEY})

    assert response.status_code == 404
    assert db.query(ApiCredential).count() == 0


def test_listing_reports_every_managed_key_even_when_unset(
    client: TestClient, db: Session
) -> None:
    """Omitting unset keys would hide an integration nobody configured."""
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))

    items = client.get("/api/v1/admin/credentials").json()["items"]

    assert {i["name"] for i in items} == {"twelve_data", "news_api", "openai", "telegram_bot"}


def test_clearing_falls_back_to_the_environment(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DELETE means "stop overriding .env", not "set empty" - and it is
    the only way back once a key has been stored."""
    monkeypatch.setattr(settings, "openai_api_key", "env-fallback-key-9999")
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))
    client.put("/api/v1/admin/credentials/openai", json={"value": _REAL_KEY})

    response = client.delete("/api/v1/admin/credentials/openai")

    assert response.status_code == 200
    assert response.json()["source"] == "environment"
    assert response.json()["is_set"] is True
    assert db.query(ApiCredential).count() == 0


def test_an_empty_value_is_rejected_rather_than_stored(
    client: TestClient, db: Session
) -> None:
    """Storing "" would look set while breaking the integration; clearing
    is what the operator means, and that is DELETE."""
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))

    assert client.put("/api/v1/admin/credentials/openai", json={"value": ""}).status_code == 422


def test_storage_disabled_is_reported_rather_than_failing_on_submit(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no master key there is nothing to encrypt with. The UI needs
    to explain that up front instead of erroring when Save is pressed."""
    monkeypatch.setattr(settings, "credential_encryption_key", "")
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))

    assert client.get("/api/v1/admin/credentials").json()["storage_enabled"] is False


def test_updating_an_existing_key_replaces_it_without_a_second_row(
    client: TestClient, db: Session
) -> None:
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))
    client.put("/api/v1/admin/credentials/openai", json={"value": _REAL_KEY})

    response = client.put(
        "/api/v1/admin/credentials/openai", json={"value": "a-rotated-key-wxyz5678"}
    )

    assert response.json()["hint"] == "5678"
    assert db.query(ApiCredential).filter_by(name="openai").count() == 1
    assert db.query(AuditLog).filter_by(action="admin_credential_updated").count() == 1


def test_unknown_uuid_name_does_not_crash(client: TestClient, db: Session) -> None:
    _as(_user(db, UserRole.SUPER_ADMIN, "root"))

    assert client.delete(f"/api/v1/admin/credentials/{uuid.uuid4()}").status_code == 404

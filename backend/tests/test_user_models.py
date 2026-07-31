import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.oauth_account_repository import OAuthAccountRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    AuditLog.__table__,
]


def _sqlite_engine_with_fk_enforcement() -> Engine:
    """SQLite ignores FK ondelete rules unless foreign_keys is explicitly enabled."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture
def session() -> Session:
    engine = _sqlite_engine_with_fk_enforcement()
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _make_user(session: Session, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": "trader@example.com",
        "username": "trader",
        "password_hash": "hashed",
    }
    defaults.update(overrides)
    user = User(**defaults)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_user_defaults() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        user = _make_user(session)

        assert user.role == UserRole.REGISTERED
        assert user.is_active is True
        assert user.is_verified is False
        assert user.timezone == "UTC"
        assert user.language == "en"


def test_user_repository_lookups(session: Session) -> None:
    _make_user(session)

    repo = UserRepository(session)
    assert repo.get_by_email("trader@example.com") is not None
    assert repo.get_by_username("trader") is not None
    assert repo.get_by_email("nobody@example.com") is None


def test_user_email_and_username_are_unique(session: Session) -> None:
    _make_user(session)

    with pytest.raises(IntegrityError):
        session.add(User(email="trader@example.com", username="other", password_hash="x"))
        session.flush()


def test_user_session_cascade_delete(session: Session) -> None:
    user = _make_user(session)
    session.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash="hashed-token",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    session.commit()

    repo = UserSessionRepository(session)
    found = repo.get_by_refresh_token_hash("hashed-token")
    assert found is not None
    assert found.user_id == user.id

    session.delete(user)
    session.commit()

    assert repo._count(repo._query()) == 0


def test_oauth_account_unique_provider_pair(session: Session) -> None:
    user = _make_user(session)
    session.add(OAuthAccount(user_id=user.id, provider="google", provider_user_id="ext-123"))
    session.commit()

    repo = OAuthAccountRepository(session)
    assert repo.get_by_provider_account("google", "ext-123") is not None

    with pytest.raises(IntegrityError):
        session.add(OAuthAccount(user_id=user.id, provider="google", provider_user_id="ext-123"))
        session.flush()


def test_audit_log_survives_user_deletion(session: Session) -> None:
    user = _make_user(session)
    session.add(
        AuditLog(user_id=user.id, action="login", resource="user", context={"ip": "127.0.0.1"})
    )
    session.commit()

    session.delete(user)
    session.commit()

    repo = AuditLogRepository(session)
    remaining = repo.list_for_user(user.id)
    # user_id is nullified, not deleted - so the direct FK lookup with the
    # original id no longer matches, but the row itself must still exist.
    assert repo._count(repo._query()) == 1
    assert remaining == []


def test_audit_log_composite_index_query(session: Session) -> None:
    user = _make_user(session)
    session.add_all(
        [
            AuditLog(user_id=user.id, action="login", resource="user"),
            AuditLog(user_id=user.id, action="logout", resource="user"),
        ]
    )
    session.commit()

    repo = AuditLogRepository(session)
    results = repo.list_for_user(user.id)
    assert len(results) == 2


def test_uuid_pk_is_generated() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        user = _make_user(session)
        assert isinstance(user.id, uuid.UUID)

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token
from app.database.base import Base
from app.exceptions import (
    InactiveAccountException,
    InvalidCredentialsException,
    InvalidRefreshTokenException,
    ResourceNotFoundException,
)
from app.models.audit_log import AuditLog
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.authentication_service import AuthenticationService

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    AuditLog.__table__,
]

_PASSWORD = "Correct-Horse9"


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


@pytest.fixture
def auth_service(session: Session) -> AuthenticationService:
    return AuthenticationService(
        UserRepository(session),
        UserSessionRepository(session),
        AuditLogRepository(session),
    )


def _make_user(session: Session, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": "trader@example.com",
        "username": "trader",
        "password_hash": hash_password(_PASSWORD),
    }
    defaults.update(overrides)
    user = User(**defaults)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _audit_actions(session: Session) -> list[str]:
    return list(session.execute(select(AuditLog.action)).scalars().all())


def test_login_success_creates_session_and_audit_log(
    auth_service: AuthenticationService, session: Session
) -> None:
    user = _make_user(session)

    logged_in_user, access_token, refresh_token = auth_service.login(
        "trader@example.com", _PASSWORD, device="pytest", ip_address="127.0.0.1"
    )

    assert logged_in_user.id == user.id
    assert access_token and refresh_token
    assert logged_in_user.last_login is not None

    stored_session = session.execute(select(UserSession)).scalar_one()
    assert stored_session.refresh_token_hash == hash_token(refresh_token)
    assert stored_session.device == "pytest"

    assert "login_success" in _audit_actions(session)


def test_login_does_not_require_is_verified(
    auth_service: AuthenticationService, session: Session
) -> None:
    _make_user(session, is_verified=False)

    # Must not raise: email verification is deferred, so login only checks
    # credentials and is_active (see BACKLOG.md).
    _, access_token, _ = auth_service.login("trader@example.com", _PASSWORD)
    assert access_token


def test_login_rejects_wrong_password(
    auth_service: AuthenticationService, session: Session
) -> None:
    _make_user(session)

    with pytest.raises(InvalidCredentialsException):
        auth_service.login("trader@example.com", "wrong-password")

    assert "login_failed" in _audit_actions(session)


def test_login_rejects_unknown_email(auth_service: AuthenticationService, session: Session) -> None:
    with pytest.raises(InvalidCredentialsException):
        auth_service.login("nobody@example.com", _PASSWORD)

    audit_entry = session.execute(select(AuditLog)).scalar_one()
    assert audit_entry.user_id is None
    assert audit_entry.action == "login_failed"


def test_login_rejects_inactive_account(
    auth_service: AuthenticationService, session: Session
) -> None:
    _make_user(session, is_active=False)

    with pytest.raises(InactiveAccountException):
        auth_service.login("trader@example.com", _PASSWORD)

    assert "login_failed" in _audit_actions(session)


def test_login_rejects_soft_deleted_account(
    auth_service: AuthenticationService, session: Session
) -> None:
    """Phase 8C (docs/59 §4/ADR-120) - a soft-deleted user must not be able
    to authenticate, even defensively checked independently of `is_active`
    (which `UserRepository.soft_delete` also sets `False`)."""
    _make_user(session, deleted_at=datetime.now(UTC))

    with pytest.raises(InactiveAccountException):
        auth_service.login("trader@example.com", _PASSWORD)

    assert "login_failed" in _audit_actions(session)


def test_refresh_issues_new_access_token(
    auth_service: AuthenticationService, session: Session
) -> None:
    user = _make_user(session)
    _, _, refresh_token = auth_service.login("trader@example.com", _PASSWORD)

    new_access_token = auth_service.refresh(refresh_token)

    from app.core.security import decode_token

    claims = decode_token(new_access_token)
    assert claims["sub"] == str(user.id)
    assert claims["type"] == "access"


def test_refresh_rejects_garbage_token(auth_service: AuthenticationService) -> None:
    with pytest.raises(InvalidRefreshTokenException):
        auth_service.refresh("not-a-real-token")


def test_refresh_rejects_access_token_used_as_refresh(
    auth_service: AuthenticationService, session: Session
) -> None:
    user = _make_user(session)
    access_token = create_access_token(user.id)

    with pytest.raises(InvalidRefreshTokenException):
        auth_service.refresh(access_token)


def test_refresh_rejects_expired_session_record(
    auth_service: AuthenticationService, session: Session
) -> None:
    user = _make_user(session)
    refresh_token = create_refresh_token(user.id)
    session.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    session.commit()

    with pytest.raises(InvalidRefreshTokenException):
        auth_service.refresh(refresh_token)


def test_logout_deletes_session_and_is_idempotent(
    auth_service: AuthenticationService, session: Session
) -> None:
    _make_user(session)
    _, _, refresh_token = auth_service.login("trader@example.com", _PASSWORD)

    auth_service.logout(refresh_token)
    assert session.execute(select(UserSession)).scalar_one_or_none() is None

    # Logging out again with the same (already-deleted) token must not raise.
    auth_service.logout(refresh_token)


def test_revoke_session_removes_it_and_audit_logs(
    auth_service: AuthenticationService, session: Session
) -> None:
    user = _make_user(session)
    _, _, _ = auth_service.login("trader@example.com", _PASSWORD)
    stored_session = session.execute(select(UserSession)).scalar_one()

    auth_service.revoke_session(user.id, stored_session.id)

    assert session.execute(select(UserSession)).scalar_one_or_none() is None
    assert "session_revoked" in _audit_actions(session)


def test_revoke_session_rejects_foreign_user(
    auth_service: AuthenticationService, session: Session
) -> None:
    _make_user(session)
    auth_service.login("trader@example.com", _PASSWORD)
    stored_session = session.execute(select(UserSession)).scalar_one()

    with pytest.raises(ResourceNotFoundException):
        auth_service.revoke_session(uuid.uuid4(), stored_session.id)


def test_revoke_all_sessions_keeps_excluded(
    auth_service: AuthenticationService, session: Session
) -> None:
    user = _make_user(session)
    session.add_all(
        [
            UserSession(
                user_id=user.id,
                refresh_token_hash="hash-1",
                expires_at=datetime.now(UTC) + timedelta(days=1),
            ),
            UserSession(
                user_id=user.id,
                refresh_token_hash="hash-2",
                expires_at=datetime.now(UTC) + timedelta(days=1),
            ),
        ]
    )
    session.commit()
    keep = session.execute(
        select(UserSession).where(UserSession.refresh_token_hash == "hash-1")
    ).scalar_one()

    revoked_count = auth_service.revoke_all_sessions(user.id, except_session_id=keep.id)

    assert revoked_count == 1
    remaining = session.execute(select(UserSession)).scalars().all()
    assert [s.id for s in remaining] == [keep.id]

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import structlog

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.exceptions import (
    InactiveAccountException,
    InvalidCredentialsException,
    InvalidRefreshTokenException,
    ResourceNotFoundException,
)
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository

logger = structlog.get_logger(__name__)


def _as_aware_utc(value: datetime) -> datetime:
    """Normalize a datetime to UTC-aware.

    SQLite (used for local/test verification, see BACKLOG.md) has no native
    timezone-aware datetime type, so `DateTime(timezone=True)` columns come
    back naive when read through it even though Postgres preserves the
    offset. Treat naive values as already UTC rather than letting the
    comparison below raise.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthenticationService:
    """Business rules for login, token refresh, logout, and session revocation.

    Login intentionally does not require `User.is_verified` - email
    verification infrastructure is deferred (see BACKLOG.md), so gating
    login on it would make every newly registered account permanently
    unusable. Only `is_active` is enforced here.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        user_session_repository: UserSessionRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._user_repository = user_repository
        self._user_session_repository = user_session_repository
        self._audit_log_repository = audit_log_repository

    def login(
        self,
        email: str,
        password: str,
        *,
        device: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        user = self._user_repository.get_by_email(email)

        if user is None or not verify_password(password, user.password_hash):
            self._audit(
                user.id if user else None,
                action="login_failed",
                resource="user",
                ip_address=ip_address,
            )
            self._commit()
            logger.warning("auth.login_failed", email=email)
            raise InvalidCredentialsException()

        if not user.is_active or user.deleted_at is not None:
            # A soft-deleted user always has is_active=False too
            # (UserRepository.soft_delete, ADR-120) - the explicit
            # `deleted_at` check here is belt-and-braces (Phase 8C, docs/59
            # §4) so login stays blocked even if is_active were ever
            # reactivated without clearing deleted_at. Reuses the same
            # exception/message as a plain suspension - deliberately not
            # distinguishing "deleted" from "inactive" to a login caller.
            self._audit(user.id, action="login_failed", resource="user", ip_address=ip_address)
            self._commit()
            logger.warning("auth.login_failed_inactive", user_id=str(user.id))
            raise InactiveAccountException()

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days)

        self._user_session_repository.create(
            UserSession(
                user_id=user.id,
                refresh_token_hash=hash_token(refresh_token),
                device=device,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at,
            )
        )
        user.last_login = datetime.now(UTC)
        self._audit(user.id, action="login_success", resource="user", ip_address=ip_address)
        self._commit()
        logger.info("auth.login_success", user_id=str(user.id))

        return user, access_token, refresh_token

    def refresh(self, refresh_token: str) -> str:
        try:
            claims = decode_token(refresh_token)
        except jwt.PyJWTError as exc:
            raise InvalidRefreshTokenException() from exc

        if claims.get("type") != "refresh":
            raise InvalidRefreshTokenException()

        session = self._user_session_repository.get_by_refresh_token_hash(hash_token(refresh_token))
        if session is None or _as_aware_utc(session.expires_at) <= datetime.now(UTC):
            raise InvalidRefreshTokenException()

        user = self._user_repository.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenException()

        return create_access_token(user.id)

    def logout(self, refresh_token: str) -> None:
        session = self._user_session_repository.get_by_refresh_token_hash(hash_token(refresh_token))
        if session is None:
            return

        user_id = session.user_id
        self._user_session_repository.delete(session)
        self._audit(user_id, action="logout", resource="user_session", resource_id=session.id)
        self._commit()
        logger.info("auth.logout", user_id=str(user_id))

    def revoke_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        session = self._user_session_repository.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise ResourceNotFoundException("Session not found.")

        self._user_session_repository.delete(session)
        self._audit(
            user_id, action="session_revoked", resource="user_session", resource_id=session_id
        )
        self._commit()
        logger.info("auth.session_revoked", user_id=str(user_id), session_id=str(session_id))

    def revoke_all_sessions(
        self, user_id: uuid.UUID, *, except_session_id: uuid.UUID | None = None
    ) -> int:
        count = self._user_session_repository.delete_for_user(user_id, exclude_id=except_session_id)
        self._audit(
            user_id,
            action="session_revoked",
            resource="user_session",
            context={"bulk": True, "count": count},
        )
        self._commit()
        logger.info("auth.sessions_revoked_bulk", user_id=str(user_id), count=count)
        return count

    def _audit(
        self,
        user_id: uuid.UUID | None,
        *,
        action: str,
        resource: str,
        resource_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip_address=ip_address,
                context=context,
            )
        )

    def _commit(self) -> None:
        self._user_repository.commit()

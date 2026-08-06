import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.dependencies.database import get_db
from app.exceptions import InactiveAccountException, InvalidAccessTokenException
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.authentication_service import AuthenticationService
from app.services.user_service import UserService

_bearer_scheme = HTTPBearer()


def get_user_service(db: Annotated[Session, Depends(get_db)]) -> UserService:
    return UserService(UserRepository(db))


def get_authentication_service(db: Annotated[Session, Depends(get_db)]) -> AuthenticationService:
    return AuthenticationService(
        UserRepository(db), UserSessionRepository(db), AuditLogRepository(db)
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Resolve the bearer access token to a `User`.

    Extract the token, decode it, verify its type, load the user, and
    reject one still-active/deleted-check: is `is_active`/`deleted_at`.
    No *other* authorization (verified/role) checks are made here - those
    remain out of scope for this phase. The active/deleted check was added
    in Phase 9B (ADR-133): an access token is otherwise valid for its full
    15-minute lifetime even after an admin disables or soft-deletes the
    account it belongs to, since `AuthenticationService.login` only
    enforces this at login. The `User` row is already loaded below for
    every authenticated request regardless, so this is a field check, not
    an added query.
    """
    try:
        claims = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenException() from exc

    if claims.get("type") != "access":
        raise InvalidAccessTokenException()

    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidAccessTokenException() from exc

    user = user_service.get_user_by_id(user_id)

    if not user.is_active or user.deleted_at is not None:
        # Same exception as the login path's equivalent check
        # (AuthenticationService.login) - deliberately does not distinguish
        # "deleted" from "inactive" to the caller.
        raise InactiveAccountException()

    return user

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.dependencies.database import get_db
from app.exceptions import InvalidAccessTokenException
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

    Intentionally minimal: extract the token, decode it, verify its type,
    and load the user. No authorization (active/verified/role) checks are
    made here - those remain out of scope for this phase.
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

    return user_service.get_user_by_id(user_id)

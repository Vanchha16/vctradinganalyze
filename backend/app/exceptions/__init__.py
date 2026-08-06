from app.exceptions.admin import LastSuperAdminException
from app.exceptions.auth import (
    DuplicateUserException,
    InactiveAccountException,
    InvalidAccessTokenException,
    InvalidCredentialsException,
    InvalidRefreshTokenException,
    RegistrationDisabledException,
    WeakPasswordException,
)
from app.exceptions.authorization import InsufficientRoleException
from app.exceptions.base import (
    AppException,
    AuthenticationException,
    BusinessException,
    ConflictException,
    PermissionDeniedException,
    ResourceNotFoundException,
    ValidationException,
)
from app.exceptions.handlers import register_exception_handlers
from app.exceptions.quota import QuotaExceededException

__all__ = [
    "AppException",
    "AuthenticationException",
    "BusinessException",
    "ConflictException",
    "DuplicateUserException",
    "InactiveAccountException",
    "InsufficientRoleException",
    "InvalidAccessTokenException",
    "InvalidCredentialsException",
    "InvalidRefreshTokenException",
    "LastSuperAdminException",
    "PermissionDeniedException",
    "QuotaExceededException",
    "RegistrationDisabledException",
    "ResourceNotFoundException",
    "ValidationException",
    "WeakPasswordException",
    "register_exception_handlers",
]

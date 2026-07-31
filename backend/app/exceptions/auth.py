from app.exceptions.base import AuthenticationException, BusinessException, ValidationException


class InvalidCredentialsException(AuthenticationException):
    """Raised when an email/password combination does not match a user."""

    error_code = "invalid_credentials"

    def __init__(self, message: str = "Invalid email or password.") -> None:
        super().__init__(message)


class InactiveAccountException(AuthenticationException):
    """Raised when a login is attempted against a deactivated account."""

    error_code = "inactive_account"

    def __init__(self, message: str = "This account is inactive.") -> None:
        super().__init__(message)


class InvalidRefreshTokenException(AuthenticationException):
    """Raised when a refresh token is malformed, expired, of the wrong type, or unknown."""

    error_code = "invalid_refresh_token"

    def __init__(self, message: str = "Invalid or expired refresh token.") -> None:
        super().__init__(message)


class InvalidAccessTokenException(AuthenticationException):
    """Raised when a bearer access token is malformed, expired, or of the wrong type."""

    error_code = "invalid_access_token"

    def __init__(self, message: str = "Invalid or expired access token.") -> None:
        super().__init__(message)


class DuplicateUserException(BusinessException):
    """Raised when registration is attempted with an email or username already in use."""

    error_code = "duplicate_user"

    def __init__(self, message: str = "Email or username is already registered.") -> None:
        super().__init__(message)


class WeakPasswordException(ValidationException):
    """Raised when a password does not meet the policy in docs/23 §7."""

    error_code = "weak_password"

    def __init__(self, message: str = "Password does not meet the required policy.") -> None:
        super().__init__(message)

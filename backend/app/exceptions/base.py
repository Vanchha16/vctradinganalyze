class AppException(Exception):
    """Base class for all application-raised exceptions.

    Carries an HTTP status code so the global handler can map it to a
    standardized error response without leaking internal details.
    """

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BusinessException(AppException):
    status_code = 400
    error_code = "business_error"


class AuthenticationException(AppException):
    status_code = 401
    error_code = "authentication_error"


class PermissionDeniedException(AppException):
    status_code = 403
    error_code = "permission_denied"


class ResourceNotFoundException(AppException):
    status_code = 404
    error_code = "resource_not_found"


class ValidationException(AppException):
    status_code = 422
    error_code = "validation_error"

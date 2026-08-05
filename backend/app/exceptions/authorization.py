from app.exceptions.base import PermissionDeniedException


class InsufficientRoleException(PermissionDeniedException):
    """Raised when an authenticated user's role does not satisfy a route's requirement."""

    error_code = "insufficient_role"

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)

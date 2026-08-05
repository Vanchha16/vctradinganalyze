from app.exceptions.base import ConflictException


class LastSuperAdminException(ConflictException):
    """Raised when an action (delete, suspend, demote) would leave zero
    active `super_admin` accounts - docs/59 §6.2/§11, ADR-121."""

    error_code = "last_super_admin"

    def __init__(
        self, message: str = "This action would leave zero active super admin accounts."
    ) -> None:
        super().__init__(message)

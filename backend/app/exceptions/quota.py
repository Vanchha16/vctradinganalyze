from app.exceptions.base import AppException


class QuotaExceededException(AppException):
    """Raised when a user has exhausted their per-bucket request quota
    within the current fixed window (`app/dependencies/quota.py`)."""

    status_code = 429
    error_code = "quota_exceeded"

    def __init__(
        self, message: str = "You have exceeded the request quota for this action."
    ) -> None:
        super().__init__(message)

from enum import StrEnum


class UserRole(StrEnum):
    """User role tiers, per docs/23_AUTHENTICATION_AND_RBAC.md §12."""

    GUEST = "guest"
    REGISTERED = "registered"
    PREMIUM = "premium"
    MODERATOR = "moderator"
    SUPPORT = "support"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

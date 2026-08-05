import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class AdminUserResponse(BaseModel):
    """docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md §6.2 - extends the
    public `UserResponse` shape with the three admin-only fields."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                "email": "trader@example.com",
                "username": "trader",
                "full_name": "Jane Trader",
                "role": "registered",
                "is_active": True,
                "is_verified": False,
                "must_change_password": True,
                "created_by_admin_id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b",
                "deleted_at": None,
                "last_login": None,
                "created_at": "2026-08-05T12:00:00Z",
            }
        },
    )

    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    must_change_password: bool
    created_by_admin_id: uuid.UUID | None
    deleted_at: datetime | None
    last_login: datetime | None
    created_at: datetime


class AdminUserCreateResponse(AdminUserResponse):
    """`temporary_password` is present only when the admin didn't supply one
    (docs/59 §6.2) - never echoes an admin-supplied password back."""

    temporary_password: str | None = None


class AdminUserDetailResponse(AdminUserResponse):
    """`GET /admin/users/{id}` - adds a count useful for the detail drawer.
    `watchlist_count` (docs/59's original sketch) is omitted - Watchlists
    (Phase 7D-A) doesn't exist yet, see the Phase 8C deviations note."""

    active_session_count: int


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])


class AdminUserCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "trader@example.com",
                "username": "trader",
                "full_name": "Jane Trader",
                "role": "registered",
                "password": None,
            }
        }
    )

    email: str = Field(pattern=_EMAIL_PATTERN, examples=["trader@example.com"])
    username: str = Field(min_length=3, max_length=50, examples=["trader"])
    full_name: str | None = Field(default=None, examples=["Jane Trader"])
    role: UserRole = Field(default=UserRole.REGISTERED)
    password: str | None = Field(
        default=None,
        min_length=12,
        description="If omitted, a temporary password is generated and returned once.",
    )


class AdminUserUpdateRequest(BaseModel):
    """Explicit allow-list only - `role`/`is_active`/`password` are
    deliberately absent, each has its own single-purpose endpoint
    (docs/59 §6.2/§11 "mass assignment")."""

    full_name: str | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: str | None = Field(default=None, pattern=_EMAIL_PATTERN)


class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool


class AdminUserRoleUpdateRequest(BaseModel):
    role: UserRole


class AdminPasswordResetResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"temporary_password": "Kx7#mPq2wRt9vLzN"}}
    )

    temporary_password: str = Field(
        description="Shown exactly once - never persisted in plaintext, never logged."
    )

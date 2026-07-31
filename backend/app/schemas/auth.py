import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    """docs/23_AUTHENTICATION_AND_RBAC.md §3 Registration Flow."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "trader@example.com",
                "username": "trader",
                "password": "Correct-Horse9",
                "full_name": "Jane Trader",
            }
        }
    )

    email: str = Field(pattern=_EMAIL_PATTERN, examples=["trader@example.com"])
    username: str = Field(min_length=3, max_length=50, examples=["trader"])
    password: str = Field(
        min_length=12,
        description="Full policy (upper/lower/number/special char) is enforced by UserService.",
        examples=["Correct-Horse9"],
    )
    full_name: str | None = Field(default=None, examples=["Jane Trader"])


class LoginRequest(BaseModel):
    """docs/23_AUTHENTICATION_AND_RBAC.md §4 Login Flow."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "trader@example.com",
                "password": "Correct-Horse9",
            }
        }
    )

    email: str = Field(pattern=_EMAIL_PATTERN, examples=["trader@example.com"])
    password: str = Field(examples=["Correct-Horse9"])


class RefreshRequest(BaseModel):
    """docs/04_API_SPECIFICATION.md POST /auth/refresh."""

    model_config = ConfigDict(json_schema_extra={"example": {"refresh_token": "eyJhbGciOi..."}})

    refresh_token: str = Field(examples=["eyJhbGciOi..."])


class LogoutRequest(BaseModel):
    """docs/04_API_SPECIFICATION.md POST /auth/logout."""

    model_config = ConfigDict(json_schema_extra={"example": {"refresh_token": "eyJhbGciOi..."}})

    refresh_token: str = Field(examples=["eyJhbGciOi..."])


class TokenResponse(BaseModel):
    """docs/04_API_SPECIFICATION.md POST /auth/login and POST /auth/refresh responses.

    `expires_in` always reflects the configured access-token lifetime
    (`settings.jwt_access_expire_minutes`) - never hardcoded.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOi...",
                "refresh_token": "eyJhbGciOi...",
                "expires_in": 900,
            }
        }
    )

    access_token: str = Field(examples=["eyJhbGciOi..."])
    refresh_token: str | None = Field(
        default=None,
        description="Omitted on /auth/refresh, which only issues a new access token.",
        examples=["eyJhbGciOi..."],
    )
    expires_in: int = Field(
        description="Access token lifetime in seconds, derived from configuration.", examples=[900]
    )


class UserResponse(BaseModel):
    """docs/04_API_SPECIFICATION.md GET /auth/me response. Never the ORM model directly."""

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
                "last_login": "2026-07-31T09:33:51Z",
                "created_at": "2026-07-30T12:00:00Z",
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
    last_login: datetime | None
    created_at: datetime

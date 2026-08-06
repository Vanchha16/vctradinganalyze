import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.oauth_account import OAuthAccount
    from app.models.telegram_account import TelegramAccount
    from app.models.user_session import UserSession


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=True),
        default=UserRole.REGISTERED,
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    """Soft-delete marker (Phase 8, ADR-120). `NULL` = active/visible; a
    deleted user is excluded from every listing and blocked from login, but
    the row itself (and everything it's a FK target of) is retained - see
    docs/59 §4 for why this project never hard-deletes a `User`."""

    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """Set whenever an admin sets a password on this user's behalf
    (creation or reset, Phase 8) - the user didn't choose it. Enforcement
    (blocking access until changed) is not built yet (docs/59 §7.1); this
    column exists so the flag is visible and future enforcement has
    something to read."""

    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    """Consecutive failed-password count since the last successful login or
    the last auto-expired lock (Phase 9B, ADR-133, docs/23 §17). Reset to
    0 on a successful login and also on the first login attempt observed
    after `locked_until` has passed."""

    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    """Set once `failed_login_attempts` reaches
    `settings.login_lockout_threshold`; `NULL` = not locked. The lock is
    temporary by design (docs/23 §17) - it expires on its own once this
    timestamp passes, rather than requiring an admin-unlock endpoint,
    because `create_admin.py` refuses a second run and there is exactly
    one admin account on a fresh deployment (Phase 9B, ADR-133)."""

    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    """Which admin created this account (Phase 8). `NULL` for the bootstrap
    super-admin and any pre-Phase-8 self-registered user - both predate
    admin-only provisioning."""

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    telegram_account: Mapped["TelegramAccount | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

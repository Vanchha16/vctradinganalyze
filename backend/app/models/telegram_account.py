import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class TelegramAccount(Base, UUIDMixin, CreatedAtMixin):
    """Links a User to a Telegram chat (docs/57 §2) - mirrors
    `OAuthAccount`'s "row exists once linking begins, filled in as the
    flow progresses" shape rather than a new pattern."""

    __tablename__ = "telegram_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    link_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    link_code_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="telegram_account")

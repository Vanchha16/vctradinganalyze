import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin
from app.models.enums import ConversationStatus, Timeframe


class Conversation(Base, UUIDMixin, TimestampMixin):
    """A user's chat conversation with the AI Chat Assistant (docs/52 §6,
    ADR-096). `TimestampMixin` (not `CreatedAtMixin`) - `title`/
    `current_symbol`/`current_timeframe`/`status` all mutate after
    creation, unlike every append-only table in this project.

    `current_symbol`/`current_timeframe` are the conversation's mutable
    "current focus" (docs/22 §10), updated whenever a message explicitly
    supplies them - distinct from `Message.symbol`/`.timeframe`, which
    are an immutable per-turn record (ADR-095).
    """

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    current_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_timeframe: Mapped[Timeframe | None] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=True
    )
    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus, name="conversation_status", native_enum=True),
        default=ConversationStatus.ACTIVE,
        nullable=False,
    )

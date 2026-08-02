import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin
from app.models.enums import MessageRole, Timeframe


class Message(Base, UUIDMixin, CreatedAtMixin):
    """One turn in a `Conversation` (docs/52 §6, ADR-096). `CreatedAtMixin`
    - a sent message is never edited, mirroring `ai_analysis`/`news_articles`.

    `symbol`/`timeframe` are this message's own immutable "referenced"
    scope (ADR-095), distinct from `Conversation.current_symbol`/
    `.current_timeframe`'s mutable "current focus". `ai_analysis_id`/
    `signal_id` use `ON DELETE SET NULL` (not `CASCADE`) - a message is a
    historical conversational record that should outlive the row it once
    referenced (docs/52 §6).
    """

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(MessageRole, name="message_role", native_enum=True), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timeframe: Mapped[Timeframe | None] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=True
    )
    ai_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ai_analysis.id", ondelete="SET NULL"), nullable=True
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

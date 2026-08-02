import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin
from app.models.enums import SignalStatus, SignalType, Timeframe


class Signal(Base, UUIDMixin, CreatedAtMixin):
    """A persisted, actionable BUY/SELL trade call (docs/03 §11, docs/51,
    ADR-086/091). Every field except `risk_reward` is reused verbatim
    from the wrapped `AIAnalysisResult` this signal derives from - see
    `analysis_id`. `CreatedAtMixin` (not `TimestampMixin`): a signal row
    is "what was recommended at time X," never rewritten in place by
    Phase 6B (ADR-091) - `status` is written once (ACTIVE) and never
    mutated by this phase's own code; `EXPIRED` is computed at read time
    only (ADR-088), never persisted back to this row.
    """

    __tablename__ = "signals"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ai_analysis.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    timeframe: Mapped[Timeframe] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=False
    )
    signal_type: Mapped[SignalType] = mapped_column(
        SAEnum(SignalType, name="signal_type", native_enum=True), nullable=False
    )
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    risk_reward: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[SignalStatus] = mapped_column(
        SAEnum(SignalStatus, name="signal_status", native_enum=True),
        default=SignalStatus.ACTIVE,
        nullable=False,
    )
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profit_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

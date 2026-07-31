import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDMixin
from app.models.enums import SMCEventStatus, SMCEventType, Timeframe

if TYPE_CHECKING:
    from app.models.asset import Asset


class SMCEvent(Base, UUIDMixin):
    """A detected Smart Money Concepts structure (docs/03 §7, docs/09,
    docs/43). Unlike `PriceCandle`/`IndicatorResult`/`AuditLog` (immutable
    once written), zone-type events (Order Blocks, FVGs, Liquidity Zones)
    are **mutable** - their `status`/`context` change as later candles
    interact with them (ADR-033, ADR-037). Rows are never deleted; a
    resolved zone transitions to ARCHIVED rather than being removed.

    `status` is an inferred addition beyond docs/03 §7's literal field
    list (id, asset_id, timeframe, event_type, price, strength, metadata,
    detected_at) - added as its own indexed column, not packed into
    `context`, so "give me all ACTIVE order blocks" is a plain filter
    rather than a JSON-operator query (ADR-037).
    """

    __tablename__ = "smc_events"
    __table_args__ = (
        Index(
            "ix_smc_events_asset_timeframe_type_status",
            "asset_id",
            "timeframe",
            "event_type",
            "status",
        ),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    timeframe: Mapped[Timeframe] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=False
    )
    event_type: Mapped[SMCEventType] = mapped_column(
        SAEnum(SMCEventType, name="smc_event_type", native_enum=True), nullable=False
    )
    status: Mapped[SMCEventStatus] = mapped_column(
        SAEnum(SMCEventStatus, name="smc_event_status", native_enum=True),
        default=SMCEventStatus.ACTIVE,
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    strength: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="smc_events")

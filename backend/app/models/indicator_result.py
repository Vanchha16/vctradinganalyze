import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDMixin
from app.models.enums import Timeframe

if TYPE_CHECKING:
    from app.models.asset import Asset


class IndicatorResult(Base, UUIDMixin):
    """A calculated indicator value, per docs/03_DATABASE_DESIGN.md §6.

    Uses its own `calculated_at` column (not CreatedAtMixin's `created_at`)
    to match the field name docs/03 specifies, and because it is
    semantically "when this was computed" rather than "when this row was
    inserted" - the same value in practice today, but a distinct concept if
    results are ever backfilled or recomputed.
    """

    __tablename__ = "indicator_results"
    __table_args__ = (
        Index(
            "ix_indicator_results_asset_timeframe_indicator", "asset_id", "timeframe", "indicator"
        ),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    timeframe: Mapped[Timeframe] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=False
    )
    indicator: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="indicator_results")

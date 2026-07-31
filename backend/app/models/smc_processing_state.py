import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDMixin
from app.models.enums import Timeframe

if TYPE_CHECKING:
    from app.models.asset import Asset


class SMCProcessingState(Base, UUIDMixin):
    """Lightweight processing checkpoint per (asset, timeframe) - not a
    detected structure itself, but bookkeeping that makes incremental
    scanning possible (docs/43, refinement 3).

    `last_processed_timestamp` is the timestamp of the last candle the
    SMC Engine has scanned - the next `analyze()` call only needs to fetch
    candles newer than this, rather than re-scanning full history.
    `engine_version` supports recovery/migration: if the detection
    algorithm changes in a way that invalidates prior results, comparing
    this against the current engine version lets a future phase decide
    whether to force a full re-scan rather than trusting stale
    incremental state.
    """

    __tablename__ = "smc_processing_states"
    __table_args__ = (
        UniqueConstraint("asset_id", "timeframe", name="uq_smc_processing_state_asset_timeframe"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    timeframe: Mapped[Timeframe] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=False
    )
    last_processed_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)

    asset: Mapped["Asset"] = relationship()

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin
from app.models.enums import Timeframe

if TYPE_CHECKING:
    from app.models.asset import Asset

_PRICE = Numeric(20, 8)


class PriceCandle(Base, UUIDMixin, CreatedAtMixin):
    """An OHLCV candle, per docs/03_DATABASE_DESIGN.md §5.

    Unique on (asset_id, timeframe, timestamp) per ADR-024 - docs/03 only
    specified an index on this triple, but docs/34's "Duplicate Detection"
    requirement implies a candle for a given asset/timeframe/timestamp is
    logically singular. Ingestion upserts on conflict (see
    PriceCandleRepository.upsert), so ADR-024's constraint is enforced as a
    correction path, not a hard rejection.
    """

    __tablename__ = "price_candles"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "timeframe", "timestamp", name="uq_price_candle_asset_timeframe_timestamp"
        ),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    timeframe: Mapped[Timeframe] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    open: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    high: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    low: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    close: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(_PRICE, nullable=True)

    asset: Mapped["Asset"] = relationship(back_populates="candles")

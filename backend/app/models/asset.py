from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin
from app.models.enums import MarketType

if TYPE_CHECKING:
    from app.models.indicator_result import IndicatorResult
    from app.models.price_candle import PriceCandle
    from app.models.smc_event import SMCEvent


class Asset(Base, UUIDMixin, TimestampMixin):
    """A tradable instrument, per docs/03_DATABASE_DESIGN.md §5.

    Uses TimestampMixin (not CreatedAtMixin) because `is_active` can be
    toggled after creation, unlike the append-only price/indicator data
    that references it.
    """

    __tablename__ = "assets"

    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market_type: Mapped[MarketType] = mapped_column(
        SAEnum(MarketType, name="market_type", native_enum=True), nullable=False
    )
    exchange: Mapped[str | None] = mapped_column(String(100), nullable=True)
    base_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    quote_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    candles: Mapped[list["PriceCandle"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    indicator_results: Mapped[list["IndicatorResult"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    smc_events: Mapped[list["SMCEvent"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

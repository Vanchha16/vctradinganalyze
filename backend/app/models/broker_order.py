import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin
from app.models.enums import OrderStatus


class BrokerOrder(Base, UUIDMixin, TimestampMixin):
    """A real order placed on the operator's Exness account via MetaApi
    (.claude/specs/phase-11-ea-bot-exness-mt5-execution.md §3B).

    One row per `Signal` that execution was attempted for - existence of
    a `BrokerOrder` row for a signal is itself the reconciliation-fork
    flag §6 relies on (`signal_monitoring_tasks.py`): if present, the
    bridge's own state drives that signal's status transitions instead
    of the existing candle-simulated touch logic. Uses `TimestampMixin`
    (not `CreatedAtMixin`) - unlike `Signal` (append-only, one row per
    recommendation), this row is mutated in place as the bridge reports
    fill/close events (`status`, `filled_price`, `closed_at`).

    `requested_price`/`filled_price` are stored separately because a
    limit order's actual fill price can differ from the price requested
    at placement time - never assume they're equal.
    """

    __tablename__ = "broker_orders"

    signal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("signals.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    broker_position_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    broker_deal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    requested_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    filled_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status", native_enum=True),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

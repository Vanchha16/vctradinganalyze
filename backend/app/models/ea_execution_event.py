import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin


class EaExecutionEvent(Base, UUIDMixin, CreatedAtMixin):
    """One thing an MT5 Expert Advisor reports it did with a signal
    (ADR-162) - a dry-run check, an order placed/skipped/rejected/cancelled,
    a fill, or a close.

    **Deliberately not `broker_orders`.** That table belongs to the dormant
    MetaApi executor, and the mere existence of a row there switches
    `signal_monitoring_tasks` into MetaApi reconciliation for the signal.
    These rows are the account's own record and never change a signal's
    status: the signal says what the analysis called, this says what one
    terminal did about it.

    Append-only (`CreatedAtMixin`): an event is a fact at a moment. A fill
    followed by a close is two rows, not one row updated.
    """

    __tablename__ = "ea_execution_events"
    __table_args__ = (
        # Idempotency: the EA derives each key from what happened (e.g.
        # `closed:<deal ticket>`), so a batch re-sent after a lost response
        # cannot store an event twice.
        Index("ix_ea_execution_events_user_event_key", "user_id", "event_key", unique=True),
        Index("ix_ea_execution_events_user_occurred", "user_id", "occurred_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    #: Which terminal reported it. SET NULL on revocation so history
    #: survives the token - `token_name` keeps it recognisable.
    token_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ea_tokens.id", ondelete="SET NULL"), nullable=True
    )
    token_name: Mapped[str] = mapped_column(String(64), nullable=False)
    signal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("signals.id", ondelete="CASCADE"), index=True, nullable=False
    )

    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    #: A `String`, not a native enum, like `signals.strategy` - adding an
    #: event type later needs no enum migration. Validated at the API.
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False)
    #: When it happened on the website's clock (the EA corrects for its
    #: own drift). `created_at` is when it arrived, which can be much
    #: later for an event queued while the terminal was offline.
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    account_login: Mapped[str] = mapped_column(String(32), nullable=False)
    broker_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    order_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: MT5 tickets are 64-bit.
    order_ticket: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    position_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    volume: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    #: Net of commission, swap and fees, in `currency` - on a cent account
    #: that is USC, not USD.
    profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)

    retcode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: `tp`, `sl`, `stop_out`, `manual`, `expert` or `other`.
    close_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)

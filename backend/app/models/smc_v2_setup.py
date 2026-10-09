import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class SmcV2State(StrEnum):
    """ADR-185. The states one smc-ict-crt-v2 design-A setup moves through.

    Stored as text (not a database enum type): adding a state later needs no
    type migration. Every change is appended to `transitions`.
    """

    #: CRT and key level passed; the M5 shift has not happened yet.
    WAITING_FOR_MSS = "waiting_for_mss"
    #: Terminal: a strategy rule said no (the frozen reason, or DATA_INCOMPLETE).
    REJECTED = "rejected"
    #: Terminal: every rule passed, but it was not published - the one slot
    #: was held, the day's cap was full, the decision was too old to act on,
    #: or the setup had expired. `reason` says which.
    NOT_PUBLISHED = "not_published"
    #: A signal exists and is pending or open.
    SIGNAL_CREATED = "signal_created"
    #: Terminal: the limit order never filled before the 3 h expiry.
    EXPIRED = "expired"
    #: Terminal: the signal was cancelled (replaced, by the website, by the EA).
    CANCELLED = "cancelled"
    #: Terminal: refused at execution (live EA/broker) - never a trade.
    EXECUTION_REJECTED = "execution_rejected"
    #: Terminal: the trade closed (stop, target or other close).
    TRADED = "traded"


TERMINAL_STATES = frozenset(
    {SmcV2State.REJECTED, SmcV2State.NOT_PUBLISHED, SmcV2State.EXPIRED, SmcV2State.CANCELLED,
     SmcV2State.EXECUTION_REJECTED, SmcV2State.TRADED}
)


class SmcV2Setup(Base, UUIDMixin, TimestampMixin):
    """One evaluated smc-ict-crt-v2 setup (ADR-185) - kept apart from v1's
    `smc_setups`, whose identity is (asset, H4 anchor) only.

    Durable identity: (asset, strategy, design, anchor timeframe, anchor
    candle). A restarted or retried run finds its row and resumes; it can
    never create a second setup - or a second signal - for the same anchor.
    """

    __tablename__ = "smc_v2_setups"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "strategy", "design", "anchor_timeframe", "anchor_t",
            name="uq_smc_v2_setups_identity",
        ),
        UniqueConstraint("signal_id", name="uq_smc_v2_setups_signal_id"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    design: Mapped[str] = mapped_column(String(8), nullable=False)
    anchor_timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    anchor_t: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    raid_t: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(96), nullable=True)
    direction: Mapped[str] = mapped_column(String(4), nullable=False)  # buy | sell
    crt_high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    crt_low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    raid_extreme: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    closed_back_inside: Mapped[bool] = mapped_column(nullable=False)
    key_levels: Mapped[str | None] = mapped_column(String(400), nullable=True)
    session: Mapped[str | None] = mapped_column(String(24), nullable=True)
    location: Mapped[str | None] = mapped_column(String(16), nullable=True)
    equilibrium: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    mss_t: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mss_level: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    entry_basis: Mapped[str | None] = mapped_column(String(16), nullable=True)
    entry: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    risk_reward: Mapped[float | None] = mapped_column(nullable=True)
    stop_distance: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    #: C11's *modelled* spread and the cost it implies in R - a decision rule
    #: recorded for audit, never a measurement of the broker's real spread.
    modelled_spread: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    modelled_cost_r: Mapped[float | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: When the deciding M5 candle closed (the earliest the decision existed).
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: When this service published the signal (decision and publication are
    #: recorded separately; publication is never back-dated).
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Broker trading day of publication (C14's cap counts these).
    trading_day: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    #: C13/C14 context at a refusal: the signal holding the slot, and the
    #: number already published that day.
    slot_signal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    published_today: Mapped[int | None] = mapped_column(Integer, nullable=True)
    news_status: Mapped[str] = mapped_column(String(32), default="NEWS_UNKNOWN", nullable=False)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )
    transitions: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)

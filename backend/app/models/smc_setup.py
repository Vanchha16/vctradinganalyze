import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class SmcSetupState(StrEnum):
    """ADR-183. The explicit states one CRT setup moves through.

    Transitions are deterministic and one-way except for the terminal
    states, and every one is appended to `transitions`. The row is the
    memory that survives a worker restart: the service never recomputes a
    setup it has already recorded.
    """

    NO_SETUP = "no_setup"
    CRT_ANCHOR_CONFIRMED = "crt_anchor_confirmed"
    RAID_CONFIRMED = "raid_confirmed"
    WAITING_FOR_M5_MSS = "waiting_for_m5_mss"
    MSS_CONFIRMED = "mss_confirmed"
    ENTRY_ZONE_CONFIRMED = "entry_zone_confirmed"
    SIGNAL_CREATED = "signal_created"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRADED = "traded"
    #: The strategy created a signal, but it was refused at execution - by
    #: the execution-safety check (impossible stop/entry geometry) or by the
    #: live EA/broker. No broker position ever existed, so this is never a
    #: trade outcome: not TRADED, not a stop-out, no R.
    EXECUTION_REJECTED = "execution_rejected"


class SmcSetup(Base, UUIDMixin, TimestampMixin):
    """One evaluated smc-ict-crt-v1 CRT setup (ADR-183).

    Every setup the service evaluates is stored, including the rejected
    ones, with the real reason - the frozen specification's rule §19
    ("never hide the actual rejection reason behind a generic WAIT").
    `anchor_t` is unique per asset, so a restart re-evaluating the same H4
    candle updates its row instead of creating a second one.
    """

    __tablename__ = "smc_setups"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: The closed H4 candle that defines the CRT range.
    anchor_t: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    state: Mapped[SmcSetupState] = mapped_column(
        SAEnum(SmcSetupState, name="smc_setup_state", native_enum=True),
        default=SmcSetupState.CRT_ANCHOR_CONFIRMED,
        nullable=False,
    )
    direction: Mapped[str | None] = mapped_column(String(4), nullable=True)  # buy | sell
    crt_high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    crt_low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    raid_t: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raid_extreme: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    closed_back_inside: Mapped[bool | None] = mapped_column(nullable=True)
    key_levels: Mapped[str | None] = mapped_column(String(400), nullable=True)
    session: Mapped[str | None] = mapped_column(String(24), nullable=True)
    location: Mapped[str | None] = mapped_column(String(16), nullable=True)  # premium|discount
    equilibrium: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    mss_t: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mss_level: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    entry_basis: Mapped[str | None] = mapped_column(String(16), nullable=True)  # fvg|ob|mss_retest
    entry: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    risk_reward: Mapped[float | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: "NEWS_UNKNOWN" whenever the news data needed is unavailable - never
    #: silently "no news" (frozen specification rule §17).
    news_status: Mapped[str] = mapped_column(String(32), default="NEWS_UNKNOWN", nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )
    #: Append-only audit of every state change: [{at, from, to, reason}].
    transitions: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)

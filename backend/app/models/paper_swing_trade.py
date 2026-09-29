import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin

_PRICE = Numeric(20, 8)
_METRIC = Numeric(12, 4)


class PaperSwingTrade(Base, UUIDMixin, TimestampMixin):
    """One swing setup and, if it was taken, its paper trade (ADR-182).

    **Deliberately not `signals`.** The EA reads its orders from `signals`
    (ADR-161); a paper trade must never be able to reach it. Nothing reads
    this table except the paper-trading service and its admin page.

    Every candidate is recorded, not only the trades: a setup the R:R or
    stop filter rejected, and one skipped because the pair already had a
    trade open, are rows too - `status` says which. The paper result is
    only comparable with the backtest if its rejections are visible.

    Updated in place when the trade closes (`TimestampMixin`), unlike the
    append-only execution events: a paper trade is one record with an
    outcome, not a stream of facts.
    """

    __tablename__ = "paper_swing_trades"
    __table_args__ = (
        # A setup is decided once: the same pullback bar, in the same
        # direction, on the same pair. Makes a re-run harmless.
        Index(
            "ix_paper_swing_trades_asset_direction_pivot",
            "asset_id",
            "direction",
            "pivot_time",
            unique=True,
        ),
        Index("ix_paper_swing_trades_signal_time", "signal_time"),
        Index("ix_paper_swing_trades_status", "status"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    setup: Mapped[str] = mapped_column(String(64), nullable=False)
    #: `buy` / `sell`. Strings, not native enums, like `signals.strategy`.
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    d1_trend: Mapped[str] = mapped_column(String(8), nullable=False)
    #: `open`, `win`, `loss`, `timeout` for a taken trade; `rejected` or
    #: `skipped` for a setup that was not.
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Why a setup was not taken: `rr_below_min`, `stop_below_min`,
    #: `no_room`, or `trade_open`.
    reject_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)

    #: When the confirming H4 bar closed - the decision, and the entry.
    signal_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pivot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pullback_level: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)

    entry_price: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    risk_pips: Mapped[Decimal] = mapped_column(_METRIC, nullable=False)
    reward_pips: Mapped[Decimal] = mapped_column(_METRIC, nullable=False)
    risk_reward: Mapped[Decimal] = mapped_column(_METRIC, nullable=False)
    atr_h4_pips: Mapped[Decimal] = mapped_column(_METRIC, nullable=False)
    #: Average daily range, 14 closed D1 bars, in pips.
    adr_pips: Mapped[Decimal | None] = mapped_column(_METRIC, nullable=True)
    spread_pips: Mapped[Decimal] = mapped_column(_METRIC, nullable=False)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(_PRICE, nullable=True)
    swap_pips: Mapped[Decimal | None] = mapped_column(_METRIC, nullable=True)
    #: Net of spread and swap, like the backtest.
    result_pips: Mapped[Decimal | None] = mapped_column(_METRIC, nullable=True)
    result_r: Mapped[Decimal | None] = mapped_column(_METRIC, nullable=True)
    holding_hours: Mapped[Decimal | None] = mapped_column(_METRIC, nullable=True)

    @property
    def is_taken(self) -> bool:
        return self.status in ("open", "win", "loss", "timeout")

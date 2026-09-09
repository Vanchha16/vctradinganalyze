from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin


class TradingViewAlert(Base, UUIDMixin, CreatedAtMixin):
    """One inbound TradingView webhook alert (ADR-146).

    Deliberately **not** a `Signal`. A `Signal` is the output of this
    project's own AI reasoning pipeline: `analysis_id` is NOT NULL and
    references `ai_analysis`, and `stop_loss`/`take_profit` are required.
    A TradingView alert has no AI analysis behind it and its payload
    carries no stop or target at all, so reusing that table would mean
    fabricating an `ai_analysis` row - inventing provenance for something
    that has none. Separate table, separate meaning.

    `CreatedAtMixin`, not `TimestampMixin`: an inbound webhook is a
    record of what arrived, never rewritten (same reasoning as
    `AuditLog`). The one exception is `delivered_at`, which records that
    the notification fired - a fact about *our* handling, not a revision
    of what was received.

    Every field except `raw_payload` is attacker-influenced: this row is
    built from an unauthenticated-until-verified HTTP body sent from the
    public internet. Types are kept deliberately loose (plain strings,
    nullable numerics) rather than mapped onto this project's internal
    enums - a third party changing their alert template must never be
    able to fail an enum lookup or wedge the ingest path. Validation
    happens at the Pydantic layer; the schema does not pretend the data
    is trusted.
    """

    __tablename__ = "tradingview_alerts"

    #: `created_at` comes from `CreatedAtMixin`, which declares no index -
    #: so the index the admin list's `ORDER BY created_at DESC` needs has
    #: to be declared here rather than via `mapped_column(index=True)`.
    #: Without this the model and the migration disagree and `alembic
    #: check` reports drift in CI (it did, on the first attempt).
    __table_args__ = (Index("ix_tradingview_alerts_created_at", "created_at"),)

    #: Raw ticker as TradingView sends it (`{{ticker}}`), e.g. "XAUUSD".
    #: Not an FK to `assets`: the alert may reference a symbol this
    #: project does not track, and rejecting it would lose the record of
    #: what was actually received.
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    exchange: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: TradingView's own interval string (`{{interval}}`) - "60", "15",
    #: "1D". Deliberately NOT mapped to this project's `Timeframe` enum:
    #: the vocabularies differ and a silent mismapping would be worse
    #: than storing what arrived verbatim.
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    #: "buy" / "sell", validated at the schema layer. A `String`, not a
    #: native enum - see the class docstring on untrusted input.
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    score: Mapped[float | None] = mapped_column(nullable=True)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    #: The alert's own `{{timenow}}`, distinct from `created_at` (when we
    #: received it). They differ under retries or delivery lag, and the
    #: gap is worth being able to see.
    alert_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Free-text provenance from the payload, e.g.
    #: "technical_heuristic_only" - the Pine scripts set this themselves
    #: to make clear they are not the backend's AI signal path.
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: The complete body as received. Kept even though every field above
    #: is parsed out of it: this is the forensic record if a template
    #: changes or a payload is ever disputed.
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    #: Set once the Telegram notification has been dispatched. `None`
    #: means never delivered (no linked accounts, or delivery failed) -
    #: delivery is best-effort and never fails the webhook.
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<TradingViewAlert {self.symbol} {self.direction} "
            f"received={self.created_at!r} id={self.id!r}>"
        )


__all__ = ["TradingViewAlert"]

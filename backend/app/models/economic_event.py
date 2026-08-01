from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin
from app.models.enums import EconomicEventCategory, EconomicEventImportance, EconomicEventStatus


class EconomicEvent(Base, UUIDMixin, TimestampMixin):
    """A macroeconomic calendar event (docs/03 §9, docs/14, docs/47 §2).

    Uses TimestampMixin (not CreatedAtMixin) - unlike News's append-only
    `news_articles`, this table is mutable: `actual`/`surprise`/`status`
    update in place as an event moves SCHEDULED -> RELEASED -> (rarely)
    REVISED (ADR-058). No separate sources table (ADR-057) - `source` is
    a plain column since this domain has no source-credibility-tier axis.

    `risk_window` and `market_bias` are deliberately NOT columns here
    (ADR-060/ADR-061) - both are computed at read time from `now` and
    this row's other fields, never persisted.
    """

    __tablename__ = "economic_events"
    __table_args__ = (
        Index(
            "ix_economic_events_natural_key",
            "country",
            "currency",
            "event_name",
            "release_time",
            unique=True,
        ),
        Index("ix_economic_events_currency_release_time", "currency", "release_time"),
        Index("ix_economic_events_importance_release_time", "importance", "release_time"),
    )

    country: Mapped[str] = mapped_column(String(2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[EconomicEventCategory] = mapped_column(
        SAEnum(EconomicEventCategory, name="economic_event_category", native_enum=True),
        nullable=False,
    )
    importance: Mapped[EconomicEventImportance] = mapped_column(
        SAEnum(EconomicEventImportance, name="economic_event_importance", native_enum=True),
        nullable=False,
    )
    forecast: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    previous: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    actual: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    surprise: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[EconomicEventStatus] = mapped_column(
        SAEnum(EconomicEventStatus, name="economic_event_status", native_enum=True),
        default=EconomicEventStatus.SCHEDULED,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    release_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

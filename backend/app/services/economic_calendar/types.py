"""Evidence dataclasses for the Economic Calendar Engine (docs/14, docs/47).

Unlike Technical Analysis/SMC/Market Regime/Confidence, this engine is not
`timeframe`-scoped - it is date/window scoped (docs/47 §9). `risk_window`
and `market_bias` are computed at read time from the row's other fields
and `now` (ADR-060/ADR-061), never persisted.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.models.enums import EconomicEventCategory, EconomicEventImportance, EconomicEventStatus


class SurpriseDirection(StrEnum):
    """docs/47 §6 - which way `actual` diverged from `forecast`."""

    HIGHER_THAN_FORECAST = "higher_than_forecast"
    LOWER_THAN_FORECAST = "lower_than_forecast"
    IN_LINE = "in_line"


class MarketBias(StrEnum):
    """docs/14 §7 / docs/47 §6 - "potential impact," never a guaranteed
    direction and never a BUY/SELL recommendation."""

    POTENTIALLY_BULLISH = "potentially_bullish"
    POTENTIALLY_BEARISH = "potentially_bearish"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class EconomicEventEvidence:
    """docs/47 §4 - the shape returned by `EconomicCalendarEngine`'s read
    path; `risk_window`/`market_bias` are computed, not stored columns."""

    id: UUID
    country: str
    currency: str
    event_name: str
    category: EconomicEventCategory
    importance: EconomicEventImportance
    forecast: Decimal | None
    previous: Decimal | None
    actual: Decimal | None
    surprise: Decimal | None
    unit: str | None
    status: EconomicEventStatus
    source: str
    release_time: datetime
    risk_window: bool
    market_bias: dict[str, MarketBias] | None


@dataclass(frozen=True, slots=True)
class EconomicCalendarResult:
    """Read-path result for `EconomicCalendarEngine.list_events`/
    `get_upcoming` (docs/47 §3, backs `GET /calendar`/`GET /calendar/upcoming`)."""

    calculated_at: datetime
    events: list[EconomicEventEvidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EconomicEventCategory, EconomicEventImportance, EconomicEventStatus
from app.services.economic_calendar.types import MarketBias


class EconomicEventResponse(BaseModel):
    """docs/04 §Economic Calendar - one calendar event, `risk_window`/
    `market_bias` computed at read time (ADR-060/ADR-061), never read
    from a stored column."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
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


class EconomicEventListResponse(BaseModel):
    items: list[EconomicEventResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])


class EconomicEventUpcomingResponse(BaseModel):
    items: list[EconomicEventResponse]

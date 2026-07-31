import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MarketType, Timeframe


class AssetResponse(BaseModel):
    """docs/04_API_SPECIFICATION.md GET /assets, GET /assets/{symbol}."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                "symbol": "EURUSD",
                "name": "Euro / US Dollar",
                "market_type": "forex",
                "exchange": None,
                "base_currency": "EUR",
                "quote_currency": "USD",
                "is_active": True,
            }
        },
    )

    id: uuid.UUID
    symbol: str
    name: str
    market_type: MarketType
    exchange: str | None
    base_currency: str | None
    quote_currency: str | None
    is_active: bool


class AssetListResponse(BaseModel):
    """Paginated asset list (docs/04 §Pagination, docs/06 §20)."""

    items: list[AssetResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])


class CandleResponse(BaseModel):
    """docs/04_API_SPECIFICATION.md GET /market/{symbol}/latest,
    GET /market/{symbol}/candles.

    No `spread` field - it isn't part of the data model (docs/03 §5 /
    `PriceCandle` don't track it), so it's omitted rather than fabricated.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "timestamp": "2026-07-31T12:00:00Z",
                "open": "1.10000",
                "high": "1.10600",
                "low": "1.09800",
                "close": "1.10500",
                "volume": None,
            }
        },
    )

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None


class CandleListResponse(BaseModel):
    symbol: str = Field(examples=["EURUSD"])
    timeframe: Timeframe
    items: list[CandleResponse]


class IndicatorResultResponse(BaseModel):
    """docs/04_API_SPECIFICATION.md GET /market/{symbol}/indicators - raw
    values only (docs/39_INDICATOR_REFERENCE.md), not the synthesized
    technical analysis `/analysis/technical/{symbol}` will return
    (Phase 4)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "indicator": "rsi_14",
                "value": "58.32",
                "metadata": None,
                "calculated_at": "2026-07-31T12:00:00Z",
            }
        },
    )

    indicator: str
    value: Decimal
    metadata: dict[str, float] | None = Field(
        validation_alias="context", serialization_alias="metadata"
    )
    calculated_at: datetime


class IndicatorListResponse(BaseModel):
    symbol: str = Field(examples=["EURUSD"])
    timeframe: Timeframe
    items: list[IndicatorResultResponse]

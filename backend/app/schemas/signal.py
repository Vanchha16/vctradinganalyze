import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Recommendation, SignalStatus, SignalType, Timeframe


class SignalResponse(BaseModel):
    """docs/51 §2/§6. `status` reflects `status_resolver.effective_status`
    (ADR-088) - a read-time value, not necessarily what's stored."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b",
                "analysis_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                "symbol": "EURUSD",
                "timeframe": "h1",
                "signal_type": "buy",
                "entry_price": 1.17540,
                "stop_loss": 1.17120,
                "take_profit": 1.18150,
                "risk_reward": 1.45,
                "confidence": 87.0,
                "status": "active",
                "triggered_at": None,
                "closed_at": None,
                "profit_loss": None,
                "created_at": "2026-08-02T12:00:00Z",
            }
        },
    )

    id: uuid.UUID
    analysis_id: uuid.UUID
    symbol: str
    timeframe: Timeframe
    signal_type: SignalType
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_reward: float
    confidence: float
    status: SignalStatus
    triggered_at: datetime | None
    closed_at: datetime | None
    profit_loss: Decimal | None
    created_at: datetime


class SignalListResponse(BaseModel):
    items: list[SignalResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])


class SignalGenerationResponse(BaseModel):
    """docs/51 §6 - `signal` is `null` when `recommendation` is `"wait"`
    (ADR-086), never a fabricated signal object."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                "symbol": "EURUSD",
                "timeframe": "h1",
                "recommendation": "buy",
                "signal": None,
            }
        }
    )

    analysis_id: uuid.UUID
    symbol: str
    timeframe: Timeframe
    recommendation: Recommendation
    signal: SignalResponse | None


class BookmarkRequest(BaseModel):
    signal_id: uuid.UUID


class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    signal_id: uuid.UUID
    created_at: datetime

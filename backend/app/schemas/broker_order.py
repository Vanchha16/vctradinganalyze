import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus


class BrokerOrderResponse(BaseModel):
    """EA Bot spec §3F - the operator must be able to see every order
    this bot has ever placed without SSHing into the box. View-only this
    phase (no manual close/modify from the dashboard, per §3's
    out-of-scope list)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b",
                "signal_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                "symbol": "XAUUSDc",
                "broker_order_id": "123456789",
                "broker_position_id": None,
                "volume": 1.36,
                "requested_price": 4422.00,
                "filled_price": None,
                "stop_loss": 4400.00,
                "take_profit": 4460.00,
                "status": "pending",
                "rejection_reason": None,
                "filled_at": None,
                "closed_at": None,
                "created_at": "2026-08-13T12:00:00Z",
            }
        },
    )

    id: uuid.UUID
    signal_id: uuid.UUID
    symbol: str
    broker_order_id: str | None
    broker_position_id: str | None
    volume: Decimal
    requested_price: Decimal
    filled_price: Decimal | None
    stop_loss: Decimal
    take_profit: Decimal
    status: OrderStatus
    rejection_reason: str | None
    filled_at: datetime | None
    closed_at: datetime | None
    created_at: datetime


class BrokerOrderListResponse(BaseModel):
    items: list[BrokerOrderResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[1])

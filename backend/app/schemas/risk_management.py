from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Timeframe
from app.services.risk_management.types import (
    PositionGuidance,
    RiskLevel,
    TradeDirection,
    TradeQualityTier,
)


class RiskEvaluationRequest(BaseModel):
    """docs/04 §Risk Management POST /risk/evaluate. Evaluates a
    caller-supplied candidate setup (ADR-062) - not a persisted Signal."""

    symbol: str
    timeframe: Timeframe
    direction: TradeDirection
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    spread: Decimal | None = Field(
        default=None, description="Optional live quote spread (ADR-065) - never fabricated."
    )


class TradeQualityBreakdownResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trend_quality: float
    technical: float
    smc: float
    risk: float
    news: float
    economic: float
    total: float


class RiskEvaluationResponse(BaseModel):
    """docs/12 §17, docs/48 §8. `breakdown` is always populated, even
    when rejected (explainability, ADR-068)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "direction": "long",
                "approved": True,
                "risk_level": "medium",
                "tier": "very_good",
                "breakdown": {
                    "trend_quality": 17.0,
                    "technical": 16.4,
                    "smc": 15.0,
                    "risk": 17.0,
                    "news": 6.5,
                    "economic": 10.0,
                    "total": 81.9,
                },
                "risk_reward": 3.15,
                "rejected_reasons": [],
                "warnings": ["High Impact News in 90 minutes"],
                "position_guidance": "normal",
                "calculated_at": "2026-08-01T12:00:00Z",
            }
        },
    )

    symbol: str
    timeframe: Timeframe
    direction: TradeDirection
    approved: bool
    risk_level: RiskLevel
    tier: TradeQualityTier
    breakdown: TradeQualityBreakdownResponse
    risk_reward: float | None
    rejected_reasons: list[str]
    warnings: list[str]
    position_guidance: PositionGuidance | None
    calculated_at: datetime

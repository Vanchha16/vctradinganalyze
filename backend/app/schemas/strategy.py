from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Timeframe
from app.services.strategy.types import StrategyName


class StrategyBreakdownResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market_match: float
    evidence_quality: float
    confidence: float
    risk: float
    historical_performance: float
    total: float


class RankedStrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy: StrategyName
    score: float


class RejectedStrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy: StrategyName
    score: float
    reason: str


class StrategyEvaluationResponse(BaseModel):
    """docs/17 §17, docs/49 §1. Strategy-methodology classification only
    - never a BUY/SELL/trade-level recommendation (ADR-069)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "primary_strategy": "trend_following",
                "alternative_strategies": [{"strategy": "pullback", "score": 82.0}],
                "rejected_strategies": [
                    {
                        "strategy": "mean_reversion",
                        "score": 42.0,
                        "reason": "Current market regime is incompatible with mean_reversion.",
                    }
                ],
                "strategy_score": 94.0,
                "breakdown": {
                    "market_match": 30.0,
                    "evidence_quality": 20.0,
                    "confidence": 17.0,
                    "risk": 15.0,
                    "historical_performance": 5.0,
                    "total": 87.0,
                },
                "warnings": [],
                "calculated_at": "2026-08-01T12:00:00Z",
            }
        },
    )

    symbol: str
    timeframe: Timeframe
    primary_strategy: StrategyName | None
    strategy_score: float | None
    breakdown: StrategyBreakdownResponse | None
    alternative_strategies: list[RankedStrategyResponse]
    rejected_strategies: list[RejectedStrategyResponse]
    warnings: list[str]
    calculated_at: datetime

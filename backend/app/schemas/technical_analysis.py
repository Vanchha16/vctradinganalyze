from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Timeframe
from app.services.technical_analysis.types import (
    MultiTimeframeVerdict,
    TrendDirection,
    TrendStrengthLevel,
)


class ScoreBreakdownResponse(BaseModel):
    """docs/42 §7 - explainable score components, not just the total
    (refinement: richer evidence for future AI reasoning)."""

    model_config = ConfigDict(from_attributes=True)

    trend: float
    momentum: float
    oscillator: float
    volume: float
    volatility: float
    support_resistance: float
    penalties: float
    total: float


class SupportResistanceLevelResponse(BaseModel):
    """docs/08 §6 - a single level with explainability metadata
    (refinement: strength + source), not just a bare price."""

    model_config = ConfigDict(from_attributes=True)

    price: Decimal
    source: str
    strength: str


class TechnicalAnalysisResponse(BaseModel):
    """docs/08 §11 canonical output shape, docs/42."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "trend": "bullish",
                "strength": "strong",
                "technical_score": 82.5,
                "score_breakdown": {
                    "trend": 25.0,
                    "momentum": 15.0,
                    "oscillator": 15.0,
                    "volume": 15.0,
                    "volatility": 10.0,
                    "support_resistance": 5.0,
                    "penalties": -2.5,
                    "total": 82.5,
                },
                "support": {"price": "1.10000", "source": "swing_low", "strength": "weak"},
                "resistance": {"price": "1.10500", "source": "daily_high", "strength": "moderate"},
                "support_levels": [],
                "resistance_levels": [],
                "indicators": {"rsi_14": 58.3, "ema_20": 1.1025},
                "warnings": [],
                "calculated_at": "2026-07-31T12:00:00Z",
            }
        },
    )

    symbol: str
    timeframe: Timeframe
    trend: TrendDirection
    strength: TrendStrengthLevel
    technical_score: float
    score_breakdown: ScoreBreakdownResponse
    support: SupportResistanceLevelResponse | None
    resistance: SupportResistanceLevelResponse | None
    support_levels: list[SupportResistanceLevelResponse]
    resistance_levels: list[SupportResistanceLevelResponse]
    indicators: dict[str, float]
    warnings: list[str]
    calculated_at: datetime


class TimeframeTrendSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timeframe: Timeframe
    direction: TrendDirection = Field(serialization_alias="trend")
    strength: TrendStrengthLevel


class MultiTimeframeAnalysisResponse(BaseModel):
    """docs/08 §8 - the combined multi-timeframe verdict, distinct from
    the single-timeframe TechnicalAnalysisResponse above."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "verdict": "bullish_alignment",
                "timeframes": [
                    {"timeframe": "d1", "trend": "bullish", "strength": "strong"},
                    {"timeframe": "h4", "trend": "bullish", "strength": "moderate"},
                    {"timeframe": "h1", "trend": "sideways", "strength": "weak"},
                    {"timeframe": "m15", "trend": "bullish", "strength": "moderate"},
                ],
            }
        },
    )

    symbol: str
    verdict: MultiTimeframeVerdict
    timeframes: list[TimeframeTrendSummaryResponse]

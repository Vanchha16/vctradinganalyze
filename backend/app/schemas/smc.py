from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import SMCEventStatus, Timeframe
from app.services.smc.types import (
    Direction,
    LiquiditySide,
    MarketStructureState,
    PremiumDiscountPosition,
    SMCVerdict,
)


class SwingClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    price: Decimal
    timestamp: datetime
    index: int


class MarketStructureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: MarketStructureState
    classifications: list[SwingClassificationResponse]


class BOSResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    direction: Direction
    break_price: Decimal
    break_time: datetime
    strength: float
    confirmed: bool


class CHOCHResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    previous_trend: MarketStructureState
    new_trend: MarketStructureState
    confidence: float
    confirmation_time: datetime


class OrderBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    direction: Direction
    zone_high: Decimal
    zone_low: Decimal
    created_at: datetime
    status: SMCEventStatus
    touched: bool
    mitigated: bool
    broken: bool
    strength_score: float
    freshness_score: float
    volume_confirmed: bool
    is_breaker: bool
    breaker_confirmed: bool
    retest_count: int


class FairValueGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    direction: Direction
    gap_high: Decimal
    gap_low: Decimal
    created_at: datetime
    status: SMCEventStatus
    gap_size: Decimal
    priority: str


class LiquidityZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    side: LiquiditySide
    level: Decimal
    touch_count: int
    status: SMCEventStatus
    created_at: datetime


class LiquiditySweepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    side: LiquiditySide
    level: Decimal
    sweep_time: datetime
    false_breakout: bool


class PremiumDiscountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: PremiumDiscountPosition
    distance: float
    range_high: Decimal
    range_low: Decimal
    equilibrium: Decimal


class ConfluenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    factors: list[str]
    confluence_score: float


class SMCScoreBreakdownResponse(BaseModel):
    """docs/43 §6 - explainable score components. `smc_score` measures
    institutional-structure evidence strength, distinct from and never
    combined with `technical_score` (ADR-036)."""

    model_config = ConfigDict(from_attributes=True)

    market_structure: float
    order_blocks: float
    fair_value_gaps: float
    liquidity: float
    premium_discount: float
    confluence: float
    penalties: float
    total: float


class SMCAnalysisResponse(BaseModel):
    """docs/09 §17 (corrected), docs/43 - structured evidence only. No
    BUY/SELL recommendations."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "market_structure": {"state": "bullish", "classifications": []},
                "bos": [],
                "choch": [],
                "order_blocks": [],
                "fair_value_gaps": [],
                "liquidity_zones": [],
                "liquidity_sweeps": [],
                "premium_discount": {
                    "position": "discount",
                    "distance": -0.4,
                    "range_high": "1.10500",
                    "range_low": "1.09500",
                    "equilibrium": "1.10000",
                },
                "confluence": {"factors": ["structure_confirmed_by_bos"], "confluence_score": 25.0},
                "smc_score": 45.0,
                "score_breakdown": {
                    "market_structure": 20.0,
                    "order_blocks": 10.0,
                    "fair_value_gaps": 0.0,
                    "liquidity": 0.0,
                    "premium_discount": 10.0,
                    "confluence": 5.0,
                    "penalties": 0.0,
                    "total": 45.0,
                },
                "warnings": [],
                "calculated_at": "2026-07-31T12:00:00Z",
            }
        },
    )

    symbol: str
    timeframe: Timeframe
    market_structure: MarketStructureResponse
    bos: list[BOSResponse]
    choch: list[CHOCHResponse]
    order_blocks: list[OrderBlockResponse]
    fair_value_gaps: list[FairValueGapResponse]
    liquidity_zones: list[LiquidityZoneResponse]
    liquidity_sweeps: list[LiquiditySweepResponse]
    premium_discount: PremiumDiscountResponse
    confluence: ConfluenceResponse
    smc_score: float
    score_breakdown: SMCScoreBreakdownResponse
    warnings: list[str]
    calculated_at: datetime


class TimeframeMarketStructureSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timeframe: Timeframe
    state: MarketStructureState


class SMCConflictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_pullback: bool
    conflicts: list[str]


class SMCMultiTimeframeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "verdict": "bullish_alignment",
                "timeframes": [
                    {"timeframe": "w1", "state": "bullish"},
                    {"timeframe": "d1", "state": "bullish"},
                    {"timeframe": "h4", "state": "bullish"},
                    {"timeframe": "h1", "state": "range"},
                    {"timeframe": "m15", "state": "bullish"},
                ],
                "conflict": {"is_pullback": False, "conflicts": []},
            }
        },
    )

    symbol: str
    verdict: SMCVerdict
    timeframes: list[TimeframeMarketStructureSummaryResponse]
    conflict: SMCConflictResponse

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import Timeframe
from app.services.market_regime.types import (
    BreakoutDirection,
    ExpansionState,
    MarketRegimeState,
    MarketRegimeVerdict,
    PullbackDepth,
    ReversalDirection,
    VolatilityRegimeState,
)
from app.services.smc.types import MarketStructureState
from app.services.technical_analysis.types import TrendDirection, TrendStrengthLevel


class TrendRegimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    direction: TrendDirection
    strength: TrendStrengthLevel
    structure_state: MarketStructureState
    aligned: bool


class VolatilityRegimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: VolatilityRegimeState
    recent_atr_average: float | None
    baseline_atr_average: float | None


class RangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_ranging: bool
    range_width: Decimal | None
    range_strength: str | None


class ExpansionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: ExpansionState
    ratio: float | None


class TransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shifting: bool
    from_hint: MarketRegimeState | None
    to_hint: MarketRegimeState | None
    confidence: float


class AccumulationDistributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    accumulation_score: float
    distribution_score: float


class BreakoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detected: bool
    direction: BreakoutDirection | None
    volume_confirmed: bool


class PullbackReversalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pullback_depth: PullbackDepth | None
    retracement_ratio: float | None
    reversal_direction: ReversalDirection | None
    reversal_confidence: float | None
    exhaustion_warning: str | None


class RegimeConfidenceBreakdownResponse(BaseModel):
    """docs/44 §6 - explainable confidence components. `confidence`
    measures how reliable this classification is, distinct from and
    never combined with `technical_score`/`smc_score` (ADR-042)."""

    model_config = ConfigDict(from_attributes=True)

    trend_clarity: float
    volatility_clarity: float
    structural_confirmation: float
    stability_penalty: float
    conflict_penalty: float
    total: float


class RegimeCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regime: MarketRegimeState
    confidence: float
    precedence: int


class MarketRegimeResponse(BaseModel):
    """docs/16 §15 (evidence-only, no strategy recommendations - see
    ADR-043), docs/44."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "regime": "trending_bullish",
                "confidence": 82.0,
                "confidence_breakdown": {
                    "trend_clarity": 35.0,
                    "volatility_clarity": 15.0,
                    "structural_confirmation": 32.0,
                    "stability_penalty": 0.0,
                    "conflict_penalty": 0.0,
                    "total": 82.0,
                },
                "trend_regime": {
                    "direction": "bullish",
                    "strength": "strong",
                    "structure_state": "bullish",
                    "aligned": True,
                },
                "volatility": {
                    "state": "normal",
                    "recent_atr_average": 1.2,
                    "baseline_atr_average": 1.1,
                },
                "range": {"is_ranging": False, "range_width": None, "range_strength": None},
                "expansion": {"state": "stable", "ratio": 1.05},
                "transition": {
                    "shifting": False,
                    "from_hint": None,
                    "to_hint": None,
                    "confidence": 0.0,
                },
                "accumulation_distribution": {"accumulation_score": 0.0, "distribution_score": 0.0},
                "breakout": {"detected": False, "direction": None, "volume_confirmed": False},
                "pullback_reversal": {
                    "pullback_depth": None,
                    "retracement_ratio": None,
                    "reversal_direction": None,
                    "reversal_confidence": None,
                    "exhaustion_warning": None,
                },
                "warnings": [],
                "calculated_at": "2026-07-31T12:00:00Z",
            }
        },
    )

    symbol: str
    timeframe: Timeframe
    regime: MarketRegimeState
    confidence: float
    confidence_breakdown: RegimeConfidenceBreakdownResponse
    trend_regime: TrendRegimeResponse
    volatility: VolatilityRegimeResponse
    range: RangeResponse
    expansion: ExpansionResponse
    transition: TransitionResponse
    accumulation_distribution: AccumulationDistributionResponse
    breakout: BreakoutResponse
    pullback_reversal: PullbackReversalResponse
    candidates: list[RegimeCandidateResponse]
    warnings: list[str]
    calculated_at: datetime


class TimeframeRegimeSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timeframe: Timeframe
    regime: MarketRegimeState


class MarketRegimeMultiTimeframeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "verdict": "bullish_alignment",
                "timeframes": [
                    {"timeframe": "w1", "regime": "trending_bullish"},
                    {"timeframe": "d1", "regime": "trending_bullish"},
                    {"timeframe": "h4", "regime": "pullback"},
                    {"timeframe": "h1", "regime": "trending_bullish"},
                    {"timeframe": "m15", "regime": "ranging"},
                ],
            }
        },
    )

    symbol: str
    verdict: MarketRegimeVerdict
    timeframes: list[TimeframeRegimeSummaryResponse]

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Timeframe
from app.schemas.market_regime import MarketRegimeResponse
from app.schemas.smc import SMCAnalysisResponse
from app.schemas.technical_analysis import TechnicalAnalysisResponse
from app.services.analysis_confidence.types import (
    ConfidenceLevel,
    ConfidenceMultiTimeframeVerdict,
    ConflictSeverity,
    NormalizedDirection,
)


class AlignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    technical_direction: NormalizedDirection | None
    smc_direction: NormalizedDirection | None
    regime_direction: NormalizedDirection | None
    agreement_ratio: float
    agreement_score: float


class ConflictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    description: str
    severity: ConflictSeverity
    engines_involved: list[str]


class ConfidenceBreakdownResponse(BaseModel):
    """docs/45 §9 - explainable, modular components. Each field is one
    independently-computed weighted contribution (docs/45 §7); future
    News/Economic/Risk inputs (Phase 5/6) add new fields here, they do
    not restructure existing ones."""

    model_config = ConfigDict(from_attributes=True)

    technical_alignment: float
    smc_alignment: float
    regime_confirmation: float
    cross_engine_agreement: float
    data_completeness: float
    freshness: float
    conflict_penalty: float
    total: float


class ConfidenceResponse(BaseModel):
    """docs/15, docs/45 - evidence-only. No BUY/SELL/WAIT recommendation
    (ADR-031, ADR-043, ADR-047). `technical`/`smc`/`market_regime` reuse
    the existing engine response schemas directly rather than
    duplicating a subset of their fields."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "timeframe": "h1",
                "overall_confidence": 78.5,
                "confidence_level": "high",
                "summary": (
                    "Confidence is high (78/100) with 3 of 3 available engines in directional "
                    "agreement. No cross-engine conflicts detected."
                ),
                "technical": None,
                "smc": None,
                "market_regime": None,
                "alignment": {
                    "technical_direction": "bullish",
                    "smc_direction": "bullish",
                    "regime_direction": "bullish",
                    "agreement_ratio": 1.0,
                    "agreement_score": 20.0,
                },
                "conflicts": [],
                "conflict_severity": "none",
                "missing_data": [],
                "warnings": [],
                "breakdown": {
                    "technical_alignment": 20.6,
                    "smc_alignment": 18.0,
                    "regime_confirmation": 16.4,
                    "cross_engine_agreement": 20.0,
                    "data_completeness": 5.0,
                    "freshness": 5.0,
                    "conflict_penalty": 0.0,
                    "total": 78.5,
                },
                "calculated_at": "2026-07-31T12:00:00Z",
            }
        },
    )

    symbol: str
    timeframe: Timeframe
    overall_confidence: float
    confidence_level: ConfidenceLevel
    summary: str
    technical: TechnicalAnalysisResponse | None
    smc: SMCAnalysisResponse | None
    market_regime: MarketRegimeResponse | None
    alignment: AlignmentResponse
    conflicts: list[ConflictResponse]
    conflict_severity: ConflictSeverity
    missing_data: list[str]
    warnings: list[str]
    breakdown: ConfidenceBreakdownResponse
    calculated_at: datetime


class TimeframeConfidenceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timeframe: Timeframe
    overall_confidence: float
    confidence_level: ConfidenceLevel


class ConfidenceMultiTimeframeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "EURUSD",
                "verdict": "aligned",
                "timeframes": [
                    {
                        "timeframe": "w1",
                        "overall_confidence": 82.0,
                        "confidence_level": "very_high",
                    },
                    {"timeframe": "d1", "overall_confidence": 76.0, "confidence_level": "high"},
                    {"timeframe": "h4", "overall_confidence": 71.0, "confidence_level": "high"},
                    {"timeframe": "h1", "overall_confidence": 69.0, "confidence_level": "high"},
                    {"timeframe": "m15", "overall_confidence": 65.0, "confidence_level": "high"},
                ],
            }
        },
    )

    symbol: str
    verdict: ConfidenceMultiTimeframeVerdict
    timeframes: list[TimeframeConfidenceSummaryResponse]

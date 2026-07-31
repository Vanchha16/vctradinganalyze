"""Evidence dataclasses for the Confidence Engine (docs/15, docs/45).

`AnalysisConfidenceEngine` produces no new market evidence of its own -
every analyzer here reframes Technical Analysis's, SMC's, and Market
Regime's already-computed output (`technical_score`/`smc_score`/
`confidence`, plus their `warnings`/`calculated_at`) into a common
confidence-evidence shape. It classifies how *trustworthy* the current
analysis is, never whether a trade will win, and never BUY/SELL/WAIT
(ADR-031, ADR-043, extended here by ADR-045/046/047).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.models.enums import Timeframe
from app.services.market_regime.types import MarketRegimeResult
from app.services.smc.types import SMCAnalysisResult
from app.services.technical_analysis.types import TechnicalAnalysisResult


class ConfidenceLevel(StrEnum):
    """docs/45 §6 - five explainable bands over the 0-100 total."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class NormalizedDirection(StrEnum):
    """The common alignment axis every engine's directional evidence is
    mapped onto (docs/45 §5) - TA's `sideways`, SMC's `range`/
    `transition`, and Regime's `ranging` all normalize to NEUTRAL rather
    than being compared as unequal strings."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ConflictSeverity(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ConflictEvidence:
    description: str
    severity: ConflictSeverity
    engines_involved: list[str]


@dataclass(frozen=True, slots=True)
class AlignmentEvidence:
    """docs/45 §5 - cross-engine directional agreement, distinct from
    each engine's own internal conflict/alignment checks."""

    technical_direction: NormalizedDirection | None
    smc_direction: NormalizedDirection | None
    regime_direction: NormalizedDirection | None
    agreement_ratio: float  # 0.0-1.0: fraction of available engines matching the majority direction
    agreement_score: float  # agreement_ratio scaled to CROSS_ENGINE_AGREEMENT_WEIGHT


@dataclass(frozen=True, slots=True)
class DataQualityEvidence:
    missing_data: list[str]
    completeness_score: float  # scaled to DATA_COMPLETENESS_WEIGHT


@dataclass(frozen=True, slots=True)
class FreshnessEvidence:
    technical_calculated_at: datetime | None
    smc_calculated_at: datetime | None
    regime_calculated_at: datetime | None
    is_stale: bool
    freshness_score: float  # scaled to FRESHNESS_WEIGHT


@dataclass(frozen=True, slots=True)
class ConfidenceBreakdown:
    """Explainable score components (mirrors ADR-028/036/042's breakdown
    pattern). Modular by construction (docs/45 §9): each component is one
    named, independently-computed weighted contribution - Phase 5/6 adds
    new named fields/weights here, it does not restructure how they're
    combined (see `confidence_aggregator.combine`)."""

    technical_alignment: float
    smc_alignment: float
    regime_confirmation: float
    cross_engine_agreement: float
    data_completeness: float
    freshness: float
    conflict_penalty: float  # <= 0

    @property
    def total(self) -> float:
        raw = (
            self.technical_alignment
            + self.smc_alignment
            + self.regime_confirmation
            + self.cross_engine_agreement
            + self.data_completeness
            + self.freshness
            + self.conflict_penalty
        )
        return max(0.0, min(100.0, raw))


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    symbol: str
    timeframe: Timeframe
    overall_confidence: float
    confidence_level: ConfidenceLevel
    summary: str
    technical: TechnicalAnalysisResult | None
    smc: SMCAnalysisResult | None
    market_regime: MarketRegimeResult | None
    alignment: AlignmentEvidence
    conflicts: list[ConflictEvidence]
    conflict_severity: ConflictSeverity
    missing_data: list[str]
    warnings: list[str]
    breakdown: ConfidenceBreakdown
    calculated_at: datetime


class ConfidenceMultiTimeframeVerdict(StrEnum):
    ALIGNED = "aligned"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class TimeframeConfidenceSummary:
    timeframe: Timeframe
    overall_confidence: float
    confidence_level: ConfidenceLevel


@dataclass(frozen=True, slots=True)
class ConfidenceMultiTimeframeResult:
    symbol: str
    verdict: ConfidenceMultiTimeframeVerdict
    timeframes: list[TimeframeConfidenceSummary] = field(default_factory=list)

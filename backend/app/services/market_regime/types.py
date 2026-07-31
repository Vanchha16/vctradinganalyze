"""Evidence dataclasses for the Market Regime Engine (docs/16, docs/44).

Every analyzer produces one of these structures, consuming Technical
Analysis's and SMC's already-computed evidence wherever possible rather
than re-deriving it. The engine classifies market conditions only - it
never produces a BUY/SELL recommendation (ADR-031, extended here).

`RegimeConfidenceBreakdown` is deliberately not named "*Score*"
(refinement from Phase 4C approval): this engine classifies, it does
not produce another evidence-strength score like `technical_score`/
`smc_score` - `confidence` measures how reliable the classification
itself is (ADR-042).
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.models.enums import Timeframe
from app.services.smc.types import MarketStructureState
from app.services.technical_analysis.types import TrendDirection, TrendStrengthLevel


class MarketRegimeState(StrEnum):
    """docs/16 §3 - the exact eleven supported regimes. Never extended
    with invented values (e.g. a bare "Expansion" or "Breakout
    Environment") - those become supporting evidence fields instead."""

    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    RANGING = "ranging"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    REVERSAL = "reversal"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNCERTAIN = "uncertain"


class VolatilityRegimeState(StrEnum):
    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


class ExpansionState(StrEnum):
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    STABLE = "stable"


class BreakoutDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    FALSE_BREAKOUT = "false_breakout"


class PullbackDepth(StrEnum):
    HEALTHY = "healthy"
    DEEP = "deep"
    POTENTIAL_REVERSAL = "potential_reversal"


class ReversalDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True, slots=True)
class TrendRegimeEvidence:
    """docs/16 §6 - combines Technical Analysis's ADX/EMA trend verdict
    with SMC's HH/HL/LH/LL structure, rather than re-deriving either."""

    direction: TrendDirection
    strength: TrendStrengthLevel
    structure_state: MarketStructureState
    aligned: bool  # TA's trend direction and SMC's structure agree


@dataclass(frozen=True, slots=True)
class VolatilityRegimeEvidence:
    """docs/16 §13. `recent_atr_average`/`baseline_atr_average` come from
    a freshly-computed ATR series (shared `wilder_smoothed_series`
    utility), not Technical Analysis's single latest ATR value, since
    classifying a *regime* needs a trend in volatility, not one point."""

    state: VolatilityRegimeState
    recent_atr_average: float | None
    baseline_atr_average: float | None


@dataclass(frozen=True, slots=True)
class RangeEvidence:
    """docs/16 §7."""

    is_ranging: bool
    range_width: Decimal | None
    range_strength: str | None  # "weak" | "moderate" | "strong"


@dataclass(frozen=True, slots=True)
class ExpansionEvidence:
    """Supporting evidence (not a top-level regime value) feeding the
    Volatility Regime classification and the RegimeClassifier."""

    state: ExpansionState
    ratio: float | None  # recent_atr_average / baseline_atr_average


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    """Within-window regime-shift detection (docs/16 has no persisted
    history to diff against - the engine is stateless, ADR-038) -
    compares the first half of the lookback window's classification
    signal to the second half's."""

    shifting: bool
    from_hint: MarketRegimeState | None
    to_hint: MarketRegimeState | None
    confidence: float


@dataclass(frozen=True, slots=True)
class AccumulationDistributionEvidence:
    """docs/16 §9/§10 - deterministic definition per ADR-040."""

    accumulation_score: float
    distribution_score: float


@dataclass(frozen=True, slots=True)
class BreakoutEvidence:
    """docs/16 §8 - `SMC`'s BOS IS the "break of key level"/"close beyond
    resistance or support" requirement; no separate break-detection."""

    detected: bool
    direction: BreakoutDirection | None
    volume_confirmed: bool


@dataclass(frozen=True, slots=True)
class PullbackReversalEvidence:
    """docs/16 §11/§12. Distinct from SMC's multi-timeframe Pullback
    (ADR-036/docs/09 §16) - this is a single-timeframe retracement-depth
    measurement (ADR-041). Reversal reuses SMC's CHOCH directly."""

    pullback_depth: PullbackDepth | None
    retracement_ratio: float | None
    reversal_direction: ReversalDirection | None
    reversal_confidence: float | None
    exhaustion_warning: str | None  # docs/16 §2's undocumented "exhaustion" folded in here


@dataclass(frozen=True, slots=True)
class RegimeConflict:
    description: str


@dataclass(frozen=True, slots=True)
class RegimeConflictReport:
    conflicts: list[RegimeConflict] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RegimeCandidate:
    """One evaluated regime condition, before the precedence rule is
    applied (refinement: evaluate all evidence first, ADR-039)."""

    regime: MarketRegimeState
    confidence: float
    precedence: int  # lower = higher priority when multiple candidates qualify


@dataclass(frozen=True, slots=True)
class RegimeConfidenceBreakdown:
    """Explainable confidence components (mirrors ADR-028/ADR-036's
    breakdown pattern) - `total` is the reported `confidence`, distinct
    from `technical_score`/`smc_score` (ADR-042)."""

    trend_clarity: float
    volatility_clarity: float
    structural_confirmation: float
    stability_penalty: float  # <= 0, from the anti-oscillation margin check (ADR-044)
    conflict_penalty: float  # <= 0

    @property
    def total(self) -> float:
        raw = (
            self.trend_clarity
            + self.volatility_clarity
            + self.structural_confirmation
            + self.stability_penalty
            + self.conflict_penalty
        )
        return max(0.0, min(100.0, raw))


@dataclass(frozen=True, slots=True)
class MarketRegimeResult:
    symbol: str
    timeframe: Timeframe
    regime: MarketRegimeState
    confidence_breakdown: RegimeConfidenceBreakdown
    trend_regime: TrendRegimeEvidence
    volatility: VolatilityRegimeEvidence
    range: RangeEvidence
    expansion: ExpansionEvidence
    transition: TransitionEvidence
    accumulation_distribution: AccumulationDistributionEvidence
    breakout: BreakoutEvidence
    pullback_reversal: PullbackReversalEvidence
    conflicts: RegimeConflictReport
    candidates: list[RegimeCandidate]
    warnings: list[str]
    calculated_at: datetime

    @property
    def confidence(self) -> float:
        return self.confidence_breakdown.total


class MarketRegimeVerdict(StrEnum):
    BULLISH_ALIGNMENT = "bullish_alignment"
    BEARISH_ALIGNMENT = "bearish_alignment"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class TimeframeRegimeSummary:
    timeframe: Timeframe
    regime: MarketRegimeState


@dataclass(frozen=True, slots=True)
class MarketRegimeMultiTimeframeResult:
    symbol: str
    verdict: MarketRegimeVerdict
    timeframes: list[TimeframeRegimeSummary]

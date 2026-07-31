"""Evidence dataclasses for the SMC Engine (docs/09, docs/43).

Every analyzer produces one of these structures. Detection components
identify structures only - they never determine whether something is a
tradeable signal (ADR-031, extended by ADR-036 for SMC).
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.models.enums import SMCEventStatus, Timeframe


class MarketStructureState(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGE = "range"
    TRANSITION = "transition"


class Direction(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class LiquiditySide(StrEnum):
    BUY_SIDE = "buy_side"
    SELL_SIDE = "sell_side"


class PremiumDiscountPosition(StrEnum):
    PREMIUM = "premium"
    DISCOUNT = "discount"
    EQUILIBRIUM = "equilibrium"


@dataclass(frozen=True, slots=True)
class SwingClassification:
    """A single swing high/low labeled HH/HL/LH/LL (docs/09 §5)."""

    kind: str  # "hh" | "hl" | "lh" | "ll"
    price: Decimal
    timestamp: datetime
    index: int


@dataclass(frozen=True, slots=True)
class MarketStructureEvidence:
    state: MarketStructureState
    classifications: list[SwingClassification] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BOSEvidence:
    direction: Direction
    break_price: Decimal
    break_time: datetime
    strength: float
    confirmed: bool


@dataclass(frozen=True, slots=True)
class CHOCHEvidence:
    previous_trend: MarketStructureState
    new_trend: MarketStructureState
    confidence: float
    confirmation_time: datetime


@dataclass(slots=True)
class OrderBlockEvidence:
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
    is_breaker: bool = False
    breaker_confirmed: bool = False
    retest_count: int = 0
    event_id: str | None = None


@dataclass(frozen=True, slots=True)
class FairValueGapEvidence:
    direction: Direction
    gap_high: Decimal
    gap_low: Decimal
    created_at: datetime
    status: SMCEventStatus
    gap_size: Decimal
    priority: str  # "high" | "medium" | "low"
    event_id: str | None = None


@dataclass(frozen=True, slots=True)
class LiquidityZoneEvidence:
    side: LiquiditySide
    level: Decimal
    touch_count: int
    status: SMCEventStatus
    created_at: datetime
    event_id: str | None = None


@dataclass(frozen=True, slots=True)
class LiquiditySweepEvidence:
    side: LiquiditySide
    level: Decimal
    sweep_time: datetime
    false_breakout: bool


@dataclass(frozen=True, slots=True)
class PremiumDiscountEvidence:
    position: PremiumDiscountPosition
    distance: float
    range_high: Decimal
    range_low: Decimal
    equilibrium: Decimal


@dataclass(frozen=True, slots=True)
class ConfluenceEvidence:
    factors: list[str]
    confluence_score: float


@dataclass(frozen=True, slots=True)
class SMCConflictReport:
    is_pullback: bool
    conflicts: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SMCScoreBreakdown:
    market_structure: float
    order_blocks: float
    fair_value_gaps: float
    liquidity: float
    premium_discount: float
    confluence: float
    penalties: float

    @property
    def total(self) -> float:
        raw = (
            self.market_structure
            + self.order_blocks
            + self.fair_value_gaps
            + self.liquidity
            + self.premium_discount
            + self.confluence
            - self.penalties
        )
        return max(0.0, min(100.0, raw))


@dataclass(frozen=True, slots=True)
class SMCAnalysisResult:
    symbol: str
    timeframe: Timeframe
    market_structure: MarketStructureEvidence
    bos: list[BOSEvidence]
    choch: list[CHOCHEvidence]
    order_blocks: list[OrderBlockEvidence]
    fair_value_gaps: list[FairValueGapEvidence]
    liquidity_zones: list[LiquidityZoneEvidence]
    liquidity_sweeps: list[LiquiditySweepEvidence]
    premium_discount: PremiumDiscountEvidence
    confluence: ConfluenceEvidence
    score_breakdown: SMCScoreBreakdown
    warnings: list[str]
    calculated_at: datetime

    @property
    def smc_score(self) -> float:
        return self.score_breakdown.total


class SMCVerdict(StrEnum):
    BULLISH_ALIGNMENT = "bullish_alignment"
    BEARISH_ALIGNMENT = "bearish_alignment"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class TimeframeMarketStructureSummary:
    timeframe: Timeframe
    state: MarketStructureState


@dataclass(frozen=True, slots=True)
class SMCMultiTimeframeResult:
    symbol: str
    verdict: SMCVerdict
    timeframes: list[TimeframeMarketStructureSummary]
    conflict: SMCConflictReport

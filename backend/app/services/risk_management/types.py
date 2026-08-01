"""Evidence dataclasses for the Risk Management Engine (docs/12, docs/48).

Nothing here is persisted (ADR-063) - `RiskManagementEngine.evaluate()`
recomputes fresh from `AnalysisConfidenceEngine`/`NewsSentimentEngine`/
`EconomicCalendarEngine` on every call. These are plain Python enums,
not SQLAlchemy-backed DB enums, since there is no table.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.models.enums import Timeframe


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class MarketSession(StrEnum):
    """docs/12 §5, docs/48 §5. `CLOSED` approximates weekend forex market
    hours (ADR-066) - not a true holiday calendar."""

    SYDNEY = "sydney"
    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    LONDON_NEW_YORK_OVERLAP = "london_new_york_overlap"
    CLOSED = "closed"


class SpreadClassification(StrEnum):
    EXCELLENT = "excellent"
    ACCEPTABLE = "acceptable"
    HIGH = "high"
    EXTREME = "extreme"


class LiquidityClassification(StrEnum):
    """docs/12 §10, docs/48 §5. `UNKNOWN` when `PriceCandle.volume` is
    unavailable - mirrors Technical Analysis's `VolumeState.UNAVAILABLE`
    precedent (ADR-066), never fabricated."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXCELLENT = "excellent"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TradeQualityTier(StrEnum):
    EXCELLENT = "excellent"
    VERY_GOOD = "very_good"
    GOOD = "good"
    AVERAGE = "average"
    REJECT = "reject"


class PositionGuidance(StrEnum):
    VERY_CONSERVATIVE = "very_conservative"
    CONSERVATIVE = "conservative"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True, slots=True)
class TradeQualityBreakdown:
    """docs/12 §15, docs/48 §7 - explainable components (mirrors
    `ConfidenceBreakdown`'s pattern, ADR-041 extended here)."""

    trend_quality: float
    technical: float
    smc: float
    risk: float
    news: float
    economic: float

    @property
    def total(self) -> float:
        raw = self.trend_quality + self.technical + self.smc + self.risk + self.news + self.economic
        return max(0.0, min(100.0, raw))


@dataclass(frozen=True, slots=True)
class RiskEvaluation:
    """docs/12 §17, docs/48 §8 - the engine's public result. `breakdown`
    is always populated, even when rejected (explainability, ADR-068)."""

    symbol: str
    timeframe: Timeframe
    direction: TradeDirection
    approved: bool
    risk_level: RiskLevel
    tier: TradeQualityTier
    breakdown: TradeQualityBreakdown
    risk_reward: float | None
    position_guidance: PositionGuidance | None
    calculated_at: datetime
    rejected_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def trade_quality(self) -> float:
        return self.breakdown.total

"""Evidence dataclasses for the Strategy Engine (docs/17, docs/49).

Nothing here is persisted (ADR-070) - `StrategyEngine.evaluate()`
recomputes fresh from `AnalysisConfidenceEngine`/`EconomicCalendarEngine`/
`risk_management` sub-modules on every call. Strategy-methodology
classification only - never a BUY/SELL/trade-level recommendation
(ADR-069, extends ADR-031/ADR-043).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.models.enums import Timeframe
from app.services.bbma.types import BBMAResult
from app.services.market_regime.types import MarketRegimeResult
from app.services.risk_management.economic_filter import EconomicFilterResult
from app.services.risk_management.types import LiquidityClassification, MarketSession
from app.services.smc.types import SMCAnalysisResult
from app.services.technical_analysis.types import TechnicalAnalysisResult


class StrategyName(StrEnum):
    """Seven strategies implemented (ADR-072) - Momentum Trading is
    deferred (no requirements defined in docs/17); Range Trading/Mean
    Reversion are merged into MEAN_REVERSION (docs/17 never defines them
    separately). Declaration order is the deterministic tie-break for
    ranking (ADR-076)."""

    TREND_FOLLOWING = "trend_following"
    SMC = "smc"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    MEAN_REVERSION = "mean_reversion"
    SCALPING = "scalping"
    SWING_TRADING = "swing_trading"
    #: ADR-148, declared genuinely last. Declaration order is the
    #: ranking tie-break (ADR-076), so inserting BBMA anywhere earlier
    #: would silently change which strategy already wins an exact tie.
    BBMA = "bbma"


@dataclass(frozen=True, slots=True)
class StrategyEvidenceBundle:
    """The shared evidence every strategy's requirements checklist and
    scoring component reads from - computed once per `evaluate()` call
    (docs/49 §3/§14) and passed to every strategy, never re-fetched per
    strategy. `technical`/`smc`/`market_regime` may be `None` if
    `AnalysisConfidenceEngine` degraded gracefully (no candle data)."""

    technical: TechnicalAnalysisResult | None
    #: ADR-148 - BBMA structure for this symbol/timeframe.
    #: `None` when there were not enough candles, exactly like
    #: the three fields below it.
    bbma: BBMAResult | None
    smc: SMCAnalysisResult | None
    market_regime: MarketRegimeResult | None
    overall_confidence: float
    session: MarketSession
    liquidity: LiquidityClassification
    economic: EconomicFilterResult


@dataclass(frozen=True, slots=True)
class RequirementsResult:
    """docs/49 §5 - `(met_count, total_count)` from one strategy's
    checklist. Ungateable requirements (no data source, e.g. Spread/RR)
    are excluded from `total_count` entirely (ADR-074) - never
    fabricated as met or unmet."""

    met_count: int
    total_count: int

    @property
    def ratio(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.met_count / self.total_count


@dataclass(frozen=True, slots=True)
class StrategyBreakdown:
    """docs/17 §14, docs/49 §7 - explainable components (mirrors
    `ConfidenceBreakdown`/`TradeQualityBreakdown`'s pattern)."""

    market_match: float
    evidence_quality: float
    confidence: float
    risk: float
    historical_performance: float

    @property
    def total(self) -> float:
        raw = (
            self.market_match
            + self.evidence_quality
            + self.confidence
            + self.risk
            + self.historical_performance
        )
        return max(0.0, min(100.0, raw))


@dataclass(frozen=True, slots=True)
class StrategyScore:
    """One strategy's full evaluation - used internally before ranking
    splits these into primary/alternative/rejected (ADR-076)."""

    strategy: StrategyName
    breakdown: StrategyBreakdown

    @property
    def total(self) -> float:
        return self.breakdown.total


@dataclass(frozen=True, slots=True)
class RankedStrategy:
    """docs/49 §8 - the bounded `alternative_strategies` shape."""

    strategy: StrategyName
    score: float


@dataclass(frozen=True, slots=True)
class RejectedStrategy:
    """docs/49 §8 - every rejected strategy carries an explicit reason."""

    strategy: StrategyName
    score: float
    reason: str


@dataclass(frozen=True, slots=True)
class StrategyEvaluation:
    """docs/17 §17, docs/49 §1 - the engine's public result. `breakdown`
    describes only `primary_strategy` (or `None` if every strategy was
    rejected)."""

    symbol: str
    timeframe: Timeframe
    primary_strategy: StrategyName | None
    strategy_score: float | None
    breakdown: StrategyBreakdown | None
    calculated_at: datetime
    alternative_strategies: list[RankedStrategy] = field(default_factory=list)
    rejected_strategies: list[RejectedStrategy] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: ADR-158. Carried through so the narration can explain a BBMA
    #: signal rather than only naming it: the prompt previously received
    #: "strategy fit: bbma (91/100)" and nothing about the Extreme, the
    #: marked level, or the retest that produced it. Present regardless
    #: of which strategy won - a losing BBMA read is still context for
    #: the `technical` section. `None` when there were no candles.
    bbma: BBMAResult | None = None

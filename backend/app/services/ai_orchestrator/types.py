"""Evidence dataclasses for the AI Orchestrator (docs/07, docs/13,
docs/50).

Nothing here reflects an AI decision except `reasoning`'s narrative text
(ADR-079) - every other field is reused verbatim from an existing engine
or computed by a deterministic module (`candidate_setup_builder.py`,
`recommendation_decision.py`, `invalidation_builder.py`,
`evidence_extractor.py`).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.models.asset import Asset
from app.models.enums import Recommendation, Timeframe
from app.services.analysis_confidence.types import ConfidenceResult
from app.services.economic_calendar.types import EconomicCalendarResult, EconomicEventEvidence
from app.services.news_sentiment.types import NewsSentimentResult
from app.services.risk_management.types import RiskEvaluation, TradeDirection
from app.services.strategy.types import StrategyEvaluation, StrategyName

from .risk_review import RiskReview


@dataclass(frozen=True, slots=True)
class CandidateSetup:
    """docs/50 §6 (ADR-080) - a deterministically-built candidate trade,
    never fabricated: entry is the latest close, stop/target are derived
    from already-computed Technical Analysis/SMC evidence."""

    direction: TradeDirection
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    """docs/50 §5 - the unified input bundle, built once per
    `AIOrchestratorEngine.generate()` call and threaded through every
    deterministic module and the prompt builder."""

    asset: Asset
    timeframe: Timeframe
    confidence: ConfidenceResult
    news: NewsSentimentResult
    economic: EconomicCalendarResult
    strategy: StrategyEvaluation
    candidate_setup: CandidateSetup | None
    risk: RiskEvaluation | None
    #: ADR-152 - one economic release the caller asked about, from the
    #: calendar's "Should I buy or sell XAUUSD?" button. Deliberately
    #: NOT merged into `economic.events`: that list feeds the
    #: deterministic risk/confidence scoring, and clicking a calendar row
    #: must not change the recommendation, only what the narration talks
    #: about (ADR-079).
    focus_event: EconomicEventEvidence | None = None
    #: ADR-165 - the same deterministic analysis, run on the timeframes
    #: above `timeframe` (H1 -> H4, D1), nearest first. Context for the
    #: narration only: `recommendation_decision` never reads it, so a
    #: higher timeframe cannot change BUY/SELL/WAIT (ADR-078/079).
    higher_timeframes: list[ConfidenceResult] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReasoningSections:
    """docs/50 §7 - the AI Orchestrator's ONLY AI-generated field. Every
    other field on `AIAnalysisResult` is deterministic (ADR-079)."""

    summary: str
    technical: str
    smc: str
    economic: str
    news: str
    risk: str
    conclusion: str


@dataclass(frozen=True, slots=True)
class AIAnalysisResult:
    """docs/07 §5, docs/13 §13, docs/50 §1 - the engine's public result.
    `id` is assigned once persisted (ADR-082)."""

    id: uuid.UUID
    symbol: str
    timeframe: Timeframe
    recommendation: Recommendation
    confidence_score: float
    confidence_level: str
    risk_level: str | None
    entry_price: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    execution_guidance: str | None
    reasoning: ReasoningSections
    model_name: str
    prompt_version: str
    ai_available: bool
    calculated_at: datetime
    #: Which strategy `StrategyEngine` ranked first for this analysis
    #: (ADR-147). `None` when every strategy was rejected - the analysis
    #: still exists, it simply has no strategy behind it, and a signal
    #: derived from it must say so rather than guessing a label.
    strategy: StrategyName | None = None
    supporting_evidence: list[str] = field(default_factory=list)
    conflicting_evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: ADR-167 - the AI risk manager's verdict on a BUY/SELL. `None` for WAIT,
    #: when the review is off, or when it failed.
    risk_review: RiskReview | None = None

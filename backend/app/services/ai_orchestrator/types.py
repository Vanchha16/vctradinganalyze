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
from app.services.economic_calendar.types import EconomicCalendarResult
from app.services.news_sentiment.types import NewsSentimentResult
from app.services.risk_management.types import RiskEvaluation, TradeDirection
from app.services.strategy.types import StrategyEvaluation


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
    supporting_evidence: list[str] = field(default_factory=list)
    conflicting_evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

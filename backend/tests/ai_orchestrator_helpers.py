"""Factory functions for building `AnalysisContext` fixtures for AI
Orchestrator unit tests - reuses `analysis_confidence_helpers`'s
`make_technical_result`/`make_smc_result`/`make_regime_result`."""

from datetime import UTC, datetime

from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.services.ai_orchestrator.types import AnalysisContext, CandidateSetup
from app.services.analysis_confidence.types import (
    AlignmentEvidence,
    ConfidenceBreakdown,
    ConfidenceLevel,
    ConfidenceResult,
    ConflictSeverity,
    NormalizedDirection,
)
from app.services.economic_calendar.types import EconomicCalendarResult
from app.services.news_sentiment.types import NewsSentimentResult
from app.services.risk_management.types import RiskEvaluation
from app.services.strategy.types import StrategyBreakdown, StrategyEvaluation, StrategyName
from tests.analysis_confidence_helpers import (
    make_regime_result,
    make_smc_result,
    make_technical_result,
)

_CALCULATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def make_asset(*, symbol: str = "EURUSD") -> Asset:
    return Asset(
        symbol=symbol,
        name="Euro / US Dollar",
        market_type=MarketType.FOREX,
        base_currency="EUR",
        quote_currency="USD",
    )


def make_confidence_result(
    *,
    overall_confidence: float = 75.0,
    confidence_level: ConfidenceLevel = ConfidenceLevel.HIGH,
    conflict_severity: ConflictSeverity = ConflictSeverity.NONE,
    include_technical: bool = True,
    include_smc: bool = True,
    include_regime: bool = True,
) -> ConfidenceResult:
    return ConfidenceResult(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        overall_confidence=overall_confidence,
        confidence_level=confidence_level,
        summary="Deterministic summary.",
        technical=make_technical_result() if include_technical else None,
        smc=make_smc_result() if include_smc else None,
        market_regime=make_regime_result() if include_regime else None,
        alignment=AlignmentEvidence(
            technical_direction=NormalizedDirection.BULLISH,
            smc_direction=NormalizedDirection.BULLISH,
            regime_direction=NormalizedDirection.BULLISH,
            agreement_ratio=1.0,
            agreement_score=20.0,
        ),
        conflicts=[],
        conflict_severity=conflict_severity,
        missing_data=[],
        warnings=[],
        breakdown=ConfidenceBreakdown(
            technical_alignment=20.0,
            smc_alignment=18.0,
            regime_confirmation=16.0,
            cross_engine_agreement=20.0,
            data_completeness=5.0,
            freshness=5.0,
            conflict_penalty=0.0,
        ),
        calculated_at=_CALCULATED_AT,
    )


def make_news_result(*, symbol: str = "EURUSD") -> NewsSentimentResult:
    return NewsSentimentResult(
        symbol=symbol, since=_CALCULATED_AT, calculated_at=_CALCULATED_AT, articles=[], warnings=[]
    )


def make_economic_result() -> EconomicCalendarResult:
    return EconomicCalendarResult(calculated_at=_CALCULATED_AT, events=[], warnings=[])


def make_strategy_evaluation(
    *, primary_strategy: StrategyName | None = StrategyName.TREND_FOLLOWING
) -> StrategyEvaluation:
    breakdown = (
        StrategyBreakdown(
            market_match=30.0,
            evidence_quality=20.0,
            confidence=17.0,
            risk=15.0,
            historical_performance=5.0,
        )
        if primary_strategy is not None
        else None
    )
    return StrategyEvaluation(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        primary_strategy=primary_strategy,
        strategy_score=breakdown.total if breakdown is not None else None,
        breakdown=breakdown,
        calculated_at=_CALCULATED_AT,
        alternative_strategies=[],
        rejected_strategies=[],
        warnings=[],
    )


def make_analysis_context(
    *,
    confidence: ConfidenceResult | None = None,
    strategy: StrategyEvaluation | None = None,
    candidate_setup: CandidateSetup | None = None,
    risk: RiskEvaluation | None = None,
) -> AnalysisContext:
    return AnalysisContext(
        asset=make_asset(),
        timeframe=Timeframe.H1,
        confidence=confidence if confidence is not None else make_confidence_result(),
        news=make_news_result(),
        economic=make_economic_result(),
        strategy=strategy if strategy is not None else make_strategy_evaluation(),
        candidate_setup=candidate_setup,
        risk=risk,
    )

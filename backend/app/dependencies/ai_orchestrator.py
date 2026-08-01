from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies.analysis_confidence import get_analysis_confidence_engine
from app.dependencies.database import get_db
from app.dependencies.economic_calendar import get_economic_calendar_engine
from app.dependencies.news import get_news_sentiment_engine
from app.dependencies.risk_management import get_risk_management_engine
from app.dependencies.strategy import get_strategy_engine
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.services.ai_orchestrator.context_builder import ContextBuilder
from app.services.ai_orchestrator.providers.base import AIProvider
from app.services.ai_orchestrator.providers.exceptions import AIProviderConfigurationError
from app.services.ai_orchestrator.providers.openai_provider import OpenAIProvider
from app.services.ai_orchestrator_engine import AIOrchestratorEngine
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.news_sentiment_engine import NewsSentimentEngine
from app.services.risk_management_engine import RiskManagementEngine
from app.services.strategy_engine import StrategyEngine

_PROVIDER_FACTORIES: dict[str, Callable[[], AIProvider]] = {
    "openai": OpenAIProvider,
}


def get_ai_provider() -> AIProvider:
    """Builds the configured AI provider (docs/50 §8, ADR-081) - mirrors
    `app.dependencies.news.get_news_providers`'s `_PROVIDER_FACTORIES`
    shape. Only the first configured provider is used (Phase 6A has
    exactly one real implementation, OpenAI - no fallback chain yet)."""
    if not settings.ai_orchestrator_providers:
        raise AIProviderConfigurationError("No AI provider configured (ai_orchestrator_providers)")

    name = settings.ai_orchestrator_providers[0]
    factory = _PROVIDER_FACTORIES.get(name)
    if factory is None:
        raise AIProviderConfigurationError(f"Unknown AI provider configured: {name!r}")
    return factory()


def get_ai_analysis_repository(db: Annotated[Session, Depends(get_db)]) -> AIAnalysisRepository:
    return AIAnalysisRepository(db)


def get_context_builder(
    confidence_engine: Annotated[AnalysisConfidenceEngine, Depends(get_analysis_confidence_engine)],
    news_sentiment_engine: Annotated[NewsSentimentEngine, Depends(get_news_sentiment_engine)],
    economic_calendar_engine: Annotated[
        EconomicCalendarEngine, Depends(get_economic_calendar_engine)
    ],
    strategy_engine: Annotated[StrategyEngine, Depends(get_strategy_engine)],
    risk_management_engine: Annotated[RiskManagementEngine, Depends(get_risk_management_engine)],
) -> ContextBuilder:
    """Composes every input `AnalysisContext` needs (docs/50 §3) - no new
    provider/repository wiring, only composition of already-existing
    engine dependencies, mirroring `app/dependencies/strategy.py`'s shape."""
    return ContextBuilder(
        confidence_engine=confidence_engine,
        news_sentiment_engine=news_sentiment_engine,
        economic_calendar_engine=economic_calendar_engine,
        strategy_engine=strategy_engine,
        risk_management_engine=risk_management_engine,
    )


def get_ai_orchestrator_engine(
    context_builder: Annotated[ContextBuilder, Depends(get_context_builder)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    ai_analysis_repository: Annotated[AIAnalysisRepository, Depends(get_ai_analysis_repository)],
) -> AIOrchestratorEngine:
    return AIOrchestratorEngine(
        context_builder=context_builder,
        provider=provider,
        ai_analysis_repository=ai_analysis_repository,
    )

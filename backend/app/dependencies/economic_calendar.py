from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies.database import get_db
from app.repositories.economic_event_repository import EconomicEventRepository
from app.services.economic_calendar.providers.base import EconomicCalendarProvider
from app.services.economic_calendar.providers.exceptions import (
    EconomicCalendarProviderConfigurationError,
)
from app.services.economic_calendar.providers.mock import MockEconomicCalendarProvider
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.economic_calendar_ingestion_pipeline import EconomicCalendarIngestionPipeline

_PROVIDER_FACTORIES: dict[str, Callable[[], EconomicCalendarProvider]] = {
    "mock": MockEconomicCalendarProvider,
}


def get_economic_calendar_providers() -> list[EconomicCalendarProvider]:
    """Build the configured economic calendar provider chain (docs/47
    §8, ADR-056). Mirrors
    `app.dependencies.news.get_news_providers` - the only place that
    knows concrete provider classes exist. No `RateLimitedProvider`
    wrapping in Phase 5B: `MockEconomicCalendarProvider` has no real
    quota to protect (same reasoning as News's Phase 5A decision).
    """
    providers: list[EconomicCalendarProvider] = []
    for name in settings.economic_calendar_providers:
        factory = _PROVIDER_FACTORIES.get(name)
        if factory is None:
            raise EconomicCalendarProviderConfigurationError(
                f"Unknown economic calendar provider configured: {name!r}"
            )
        providers.append(factory())
    return providers


def get_economic_event_repository(
    db: Annotated[Session, Depends(get_db)],
) -> EconomicEventRepository:
    return EconomicEventRepository(db)


def get_economic_calendar_engine(
    event_repository: Annotated[EconomicEventRepository, Depends(get_economic_event_repository)],
) -> EconomicCalendarEngine:
    return EconomicCalendarEngine(event_repository)


def get_economic_calendar_ingestion_pipeline(
    db: Annotated[Session, Depends(get_db)],
) -> EconomicCalendarIngestionPipeline:
    return EconomicCalendarIngestionPipeline(
        providers=get_economic_calendar_providers(),
        event_repository=EconomicEventRepository(db),
    )

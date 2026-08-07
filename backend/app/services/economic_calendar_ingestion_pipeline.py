"""Write-path orchestrator for the Economic Calendar Engine (docs/47
§3), Celery-triggered rather than API-triggered. Kept separate from
`EconomicCalendarEngine` (the read path) since ingestion is a scheduled
producer concern, not an on-demand query.

Fetch a bounded `[now - lookback, now + lookahead]` window -> classify
(category/importance) -> calculate surprise -> **upsert** by natural key
(ADR-058) - the key divergence from News's insert-skip-on-duplicate
pattern, since the same economic event is re-fetched repeatedly as it
moves SCHEDULED -> RELEASED -> (rarely) REVISED.

**Phase 9G (ADR-139):** `run()` used to return a bare `(created,
updated)` tuple and log a provider failure at `warning` - the mirror-
image problem to News: this pipeline *does* produce data, but
`GET /calendar` could be silently serving synthetic mock events with
nothing indicating the configured provider is a mock. `run()` now
returns `CalendarIngestionResult` (per-provider outcomes) and raises
`AllEconomicCalendarProvidersFailedError` if every configured provider
failed - callers must not treat that as a clean success.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog

from app.models.economic_event import EconomicEvent
from app.models.enums import EconomicEventCategory, EconomicEventImportance, EconomicEventStatus
from app.repositories.economic_event_repository import EconomicEventRepository
from app.services.economic_calendar import (
    category_classifier,
    importance_scorer,
    surprise_calculator,
)
from app.services.economic_calendar.providers.base import EconomicCalendarProvider, RawEconomicEvent
from app.services.economic_calendar.providers.exceptions import (
    AllEconomicCalendarProvidersFailedError,
    EconomicCalendarProviderError,
)
from app.services.ingestion_health import ProviderOutcome

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CalendarIngestionResult:
    created: int
    updated: int
    provider_outcomes: list[ProviderOutcome]


class EconomicCalendarIngestionPipeline:
    def __init__(
        self,
        *,
        providers: list[EconomicCalendarProvider],
        event_repository: EconomicEventRepository,
    ) -> None:
        self._providers = providers
        self._event_repository = event_repository

    @property
    def provider_names(self) -> list[str]:
        return [p.name for p in self._providers]

    @property
    def uses_mock(self) -> bool:
        return any(p.name == "mock" for p in self._providers)

    def run(self, start: datetime, end: datetime) -> CalendarIngestionResult:
        """Ingests events with `release_time` in `[start, end]`. Raises
        `AllEconomicCalendarProvidersFailedError` if every configured
        provider failed - a genuinely empty result (every provider
        succeeded but returned nothing) is never conflated with that.
        Per-provider resilience is unchanged."""
        created = 0
        updated = 0
        provider_outcomes: list[ProviderOutcome] = []

        for provider in self._providers:
            try:
                raw_events = provider.fetch_events(start, end)
            except EconomicCalendarProviderError as exc:
                logger.error(
                    "calendar_ingestion.provider_call",
                    provider=provider.name,
                    outcome="error",
                    error=str(exc),
                )
                provider_outcomes.append(
                    ProviderOutcome(provider=provider.name, success=False, error=str(exc))
                )
                continue

            logger.info(
                "calendar_ingestion.provider_call",
                provider=provider.name,
                outcome="success",
                event_count=len(raw_events),
            )
            provider_outcomes.append(
                ProviderOutcome(provider=provider.name, success=True, count=len(raw_events))
            )

            for raw_event in raw_events:
                was_created = self._upsert(raw_event)
                if was_created:
                    created += 1
                else:
                    updated += 1

        self._event_repository.commit()

        if provider_outcomes and all(not o.success for o in provider_outcomes):
            failures = "; ".join(f"{o.provider}: {o.error}" for o in provider_outcomes)
            logger.error("calendar_ingestion.all_providers_failed", error=failures)
            raise AllEconomicCalendarProvidersFailedError(
                f"Every configured economic calendar provider failed: {failures}"
            )

        return CalendarIngestionResult(
            created=created, updated=updated, provider_outcomes=provider_outcomes
        )

    def _upsert(self, raw_event: RawEconomicEvent) -> bool:
        """Returns True if a new row was created, False if an existing
        row was found (and possibly updated)."""
        category = category_classifier.classify(raw_event.event_name)
        importance = importance_scorer.score(category, raw_event.event_name)
        surprise = surprise_calculator.calculate(raw_event.actual, raw_event.forecast)

        existing = self._event_repository.get_by_natural_key(
            raw_event.country, raw_event.currency, raw_event.event_name, raw_event.release_time
        )

        if existing is None:
            status = (
                EconomicEventStatus.RELEASED
                if raw_event.actual is not None
                else (EconomicEventStatus.SCHEDULED)
            )
            self._event_repository.create(
                EconomicEvent(
                    country=raw_event.country,
                    currency=raw_event.currency,
                    event_name=raw_event.event_name,
                    category=category,
                    importance=importance,
                    forecast=raw_event.forecast,
                    previous=raw_event.previous,
                    actual=raw_event.actual,
                    surprise=surprise,
                    unit=raw_event.unit,
                    status=status,
                    source=raw_event.source_name,
                    release_time=raw_event.release_time,
                )
            )
            return True

        self._apply_updates(existing, raw_event, category, importance, surprise)
        return False

    @staticmethod
    def _apply_updates(
        existing: EconomicEvent,
        raw_event: RawEconomicEvent,
        category: EconomicEventCategory,
        importance: EconomicEventImportance,
        surprise: Decimal | None,
    ) -> None:
        if raw_event.actual is not None and existing.actual is not None:
            if existing.actual != raw_event.actual:
                existing.status = EconomicEventStatus.REVISED
        elif raw_event.actual is not None and existing.actual is None:
            existing.status = EconomicEventStatus.RELEASED

        existing.category = category
        existing.importance = importance
        existing.forecast = raw_event.forecast
        existing.previous = raw_event.previous
        existing.actual = raw_event.actual
        existing.surprise = surprise
        existing.unit = raw_event.unit
        existing.source = raw_event.source_name


def default_window(lookback_days: int, lookahead_days: int) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    return now - timedelta(days=lookback_days), now + timedelta(days=lookahead_days)

"""Write-path orchestrator for the Economic Calendar Engine (docs/47
§3), Celery-triggered rather than API-triggered. Kept separate from
`EconomicCalendarEngine` (the read path) since ingestion is a scheduled
producer concern, not an on-demand query.

Fetch a bounded `[now - lookback, now + lookahead]` window -> classify
(category/importance) -> calculate surprise -> **upsert** by natural key
(ADR-058) - the key divergence from News's insert-skip-on-duplicate
pattern, since the same economic event is re-fetched repeatedly as it
moves SCHEDULED -> RELEASED -> (rarely) REVISED.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.economic_event import EconomicEvent
from app.models.enums import EconomicEventCategory, EconomicEventImportance, EconomicEventStatus
from app.repositories.economic_event_repository import EconomicEventRepository
from app.services.economic_calendar import (
    category_classifier,
    importance_scorer,
    surprise_calculator,
)
from app.services.economic_calendar.providers.base import EconomicCalendarProvider, RawEconomicEvent
from app.services.economic_calendar.providers.exceptions import EconomicCalendarProviderError

logger = logging.getLogger(__name__)


class EconomicCalendarIngestionPipeline:
    def __init__(
        self,
        *,
        providers: list[EconomicCalendarProvider],
        event_repository: EconomicEventRepository,
    ) -> None:
        self._providers = providers
        self._event_repository = event_repository

    def run(self, start: datetime, end: datetime) -> tuple[int, int]:
        """Ingests events with `release_time` in `[start, end]`. Returns
        `(created_count, updated_count)`."""
        created = 0
        updated = 0

        for provider in self._providers:
            try:
                raw_events = provider.fetch_events(start, end)
            except EconomicCalendarProviderError as exc:
                logger.warning("Economic calendar provider %s failed: %s", provider.name, exc)
                continue

            for raw_event in raw_events:
                was_created = self._upsert(raw_event)
                if was_created:
                    created += 1
                else:
                    updated += 1

        self._event_repository.commit()
        return created, updated

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

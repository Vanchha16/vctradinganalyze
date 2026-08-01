"""Read-path orchestrator for the Economic Calendar Engine (docs/47
§1/§3).

Unlike Technical Analysis/SMC/Market Regime/Confidence, this engine
never recomputes evidence from candles - it queries already-persisted
`EconomicEvent` rows (written by `EconomicCalendarIngestionPipeline`,
the separate write-path orchestrator) and computes `risk_window`/
`market_bias` fresh on every read (ADR-060/ADR-061). See docs/47 §9 for
why this engine has no `timeframe` parameter.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from app.models.economic_event import EconomicEvent
from app.models.enums import EconomicEventCategory, EconomicEventImportance
from app.repositories.economic_event_repository import EconomicEventRepository
from app.services.economic_calendar import bias_analyzer, risk_window, surprise_calculator
from app.services.economic_calendar.types import (
    EconomicCalendarResult,
    EconomicEventEvidence,
    MarketBias,
)

_UPCOMING_IMPORTANCES = (EconomicEventImportance.CRITICAL, EconomicEventImportance.HIGH)


class EconomicCalendarEngine:
    def __init__(self, event_repository: EconomicEventRepository) -> None:
        self._event_repository = event_repository

    def list_events(
        self,
        *,
        country: str | None = None,
        currency: str | None = None,
        importance: EconomicEventImportance | None = None,
        category: EconomicEventCategory | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[EconomicCalendarResult, int]:
        rows = self._event_repository.find_paginated(
            country=country,
            currency=currency,
            importance=importance,
            category=category,
            start=start,
            end=end,
            offset=offset,
            limit=limit,
        )
        total = self._event_repository.count_filtered(
            country=country,
            currency=currency,
            importance=importance,
            category=category,
            start=start,
            end=end,
        )
        return self._to_result(rows), total

    def get_upcoming(self, *, limit: int = 20) -> EconomicCalendarResult:
        now = datetime.now(UTC)
        rows = self._event_repository.find_upcoming(
            since=now, importances=_UPCOMING_IMPORTANCES, limit=limit
        )
        return self._to_result(rows)

    def get_by_id(self, event_id: uuid.UUID) -> EconomicEventEvidence | None:
        event = self._event_repository.get_by_id(event_id)
        if event is None:
            return None
        return self._to_evidence(event, datetime.now(UTC))

    def _to_result(self, rows: Sequence[EconomicEvent]) -> EconomicCalendarResult:
        now = datetime.now(UTC)
        return EconomicCalendarResult(
            calculated_at=now,
            events=[self._to_evidence(row, now) for row in rows],
        )

    @staticmethod
    def _to_evidence(event: EconomicEvent, now: datetime) -> EconomicEventEvidence:
        market_bias: dict[str, MarketBias] | None = None
        if event.actual is not None:
            surprise: Decimal | None = event.surprise
            direction = surprise_calculator.direction_of(surprise)
            market_bias = bias_analyzer.analyze(event.category, direction)

        return EconomicEventEvidence(
            id=event.id,
            country=event.country,
            currency=event.currency,
            event_name=event.event_name,
            category=event.category,
            importance=event.importance,
            forecast=event.forecast,
            previous=event.previous,
            actual=event.actual,
            surprise=event.surprise,
            unit=event.unit,
            status=event.status,
            source=event.source,
            release_time=event.release_time,
            risk_window=risk_window.is_in_risk_window(now, event.release_time, event.importance),
            market_bias=market_bias,
        )

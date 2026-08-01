import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.models.economic_event import EconomicEvent
from app.models.enums import EconomicEventCategory, EconomicEventImportance
from app.repositories.base import BaseRepository


class EconomicEventRepository(BaseRepository[EconomicEvent]):
    model = EconomicEvent

    def create(self, event: EconomicEvent) -> EconomicEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def get_by_id(self, event_id: uuid.UUID) -> EconomicEvent | None:
        return self.session.get(EconomicEvent, event_id)

    def get_by_natural_key(
        self, country: str, currency: str, event_name: str, release_time: datetime
    ) -> EconomicEvent | None:
        """`(country, currency, event_name, release_time)` identifies
        "the same event" across repeated ingestion runs - used to upsert
        in place as an event moves SCHEDULED -> RELEASED -> REVISED
        (ADR-058), mirroring `SMCEventRepository.get_by_natural_key`."""
        query = self._filter_by(
            self._query(),
            country=country,
            currency=currency,
            event_name=event_name,
            release_time=release_time,
        )
        return self.session.execute(query).scalar_one_or_none()

    def find_paginated(
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
    ) -> Sequence[EconomicEvent]:
        query = self._filter_by(
            self._query(), **self._build_filters(country, currency, importance, category)
        )
        if start is not None:
            query = query.where(EconomicEvent.release_time >= start)
        if end is not None:
            query = query.where(EconomicEvent.release_time <= end)
        query = query.order_by(EconomicEvent.release_time.asc())
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def count_filtered(
        self,
        *,
        country: str | None = None,
        currency: str | None = None,
        importance: EconomicEventImportance | None = None,
        category: EconomicEventCategory | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        query = self._filter_by(
            self._query(), **self._build_filters(country, currency, importance, category)
        )
        if start is not None:
            query = query.where(EconomicEvent.release_time >= start)
        if end is not None:
            query = query.where(EconomicEvent.release_time <= end)
        return self._count(query)

    def find_upcoming(
        self, *, since: datetime, importances: Sequence[EconomicEventImportance], limit: int = 20
    ) -> Sequence[EconomicEvent]:
        query = (
            select(EconomicEvent)
            .where(EconomicEvent.release_time >= since)
            .where(EconomicEvent.importance.in_(importances))
            .order_by(EconomicEvent.release_time.asc())
            .limit(limit)
        )
        return self.session.execute(query).scalars().all()

    @staticmethod
    def _build_filters(
        country: str | None,
        currency: str | None,
        importance: EconomicEventImportance | None,
        category: EconomicEventCategory | None,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if country is not None:
            filters["country"] = country
        if currency is not None:
            filters["currency"] = currency
        if importance is not None:
            filters["importance"] = importance
        if category is not None:
            filters["category"] = category
        return filters

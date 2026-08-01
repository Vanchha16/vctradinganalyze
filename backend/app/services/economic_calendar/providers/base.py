from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawEconomicEvent:
    """An economic calendar event as returned by a provider, before
    category/importance classification (docs/47 §3). Values are left as
    the provider returned them - the ingestion pipeline's analyzer
    modules derive `category`/`importance`/`surprise` from this raw
    shape."""

    country: str
    currency: str
    event_name: str
    release_time: datetime
    source_name: str
    forecast: Decimal | None = None
    previous: Decimal | None = None
    actual: Decimal | None = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class EconomicCalendarProviderCapabilities:
    """What an economic calendar provider can be asked to do (docs/47 §8)."""

    supported_countries: frozenset[str]
    max_lookahead_days: int | None = None
    max_lookback_days: int | None = None


class EconomicCalendarProvider(Protocol):
    """Interface every economic calendar provider implements (docs/47
    §8, ADR-056).

    `EconomicCalendarIngestionPipeline` depends only on this interface,
    never on a concrete provider class - mirrors
    `app.services.news.providers.base.NewsProvider`, except
    `fetch_events` takes an explicit `[start, end]` window rather than a
    single `since` cutoff (ADR-056): economic events are scheduled ahead
    of time, so the same call must cover both past (revisions) and
    future (upcoming schedule) events.
    """

    name: str

    def fetch_events(self, start: datetime, end: datetime) -> list[RawEconomicEvent]:
        """Fetch events with `release_time` in `[start, end]` (UTC-aware).

        Raises `TransientEconomicCalendarProviderError` for retryable
        failures, `PermanentEconomicCalendarProviderError` (or a more
        specific subclass) for failures that should not be retried.
        """
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not fetch real data."""
        ...

    def capabilities(self) -> EconomicCalendarProviderCapabilities:
        """Declare what this provider supports."""
        ...


__all__ = ["EconomicCalendarProvider", "EconomicCalendarProviderCapabilities", "RawEconomicEvent"]

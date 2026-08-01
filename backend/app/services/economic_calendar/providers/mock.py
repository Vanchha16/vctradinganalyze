import hashlib
import random
from datetime import UTC, datetime
from decimal import Decimal

from app.services.economic_calendar.providers.base import (
    EconomicCalendarProviderCapabilities,
    RawEconomicEvent,
)

_CAPABILITIES = EconomicCalendarProviderCapabilities(
    supported_countries=frozenset({"US", "EU", "GB", "JP", "AU"}),
    max_lookahead_days=60,
    max_lookback_days=30,
)

# (country, currency, event_name, forecast, previous, unit) - deliberately
# spans every docs/14 §3 category so a single fetch exercises every
# downstream classifier (docs/47 §5).
_TEMPLATE_EVENTS: list[tuple[str, str, str, float, float, str]] = [
    ("US", "USD", "CPI y/y", 3.2, 3.5, "%"),
    ("US", "USD", "Non-Farm Payrolls", 180.0, 175.0, "K"),
    ("US", "USD", "FOMC Interest Rate Decision", 5.25, 5.25, "%"),
    ("US", "USD", "GDP q/q", 2.1, 1.9, "%"),
    ("US", "USD", "Retail Sales m/m", 0.4, 0.3, "%"),
    ("US", "USD", "Consumer Confidence", 102.0, 100.0, ""),
    ("US", "USD", "Building Permits", 1.45, 1.42, "M"),
    ("US", "USD", "Trade Balance", -65.0, -63.0, "B"),
    ("EU", "EUR", "ECB Interest Rate Decision", 4.5, 4.5, "%"),
    ("GB", "GBP", "Services PMI", 51.2, 50.8, ""),
]


def _seed_for(start: datetime, end: datetime) -> int:
    """A stable seed derived from the request window, independent of
    Python's per-process hash randomization - mirrors
    `app.services.news.providers.mock._seed_for`."""
    digest = hashlib.sha256(f"{start.isoformat()}:{end.isoformat()}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


class MockEconomicCalendarProvider:
    """Synthetic economic calendar generator for Phase 5B (docs/47 §8,
    ADR-056). Never fails, never calls an external service - a real
    vendor (TradingEconomics) is deferred to a follow-up sub-phase."""

    name = "mock"

    def fetch_events(self, start: datetime, end: datetime) -> list[RawEconomicEvent]:
        rng = random.Random(_seed_for(start, end))
        now = datetime.now(UTC)
        window_seconds = max(1.0, (end - start).total_seconds())

        events: list[RawEconomicEvent] = []
        for country, currency, event_name, forecast, previous, unit in _TEMPLATE_EVENTS:
            offset_seconds = rng.uniform(0, window_seconds)
            release_time = start + (end - start) * (offset_seconds / window_seconds)

            actual: Decimal | None = None
            if release_time <= now:
                noise = rng.uniform(-0.15, 0.15) * (abs(forecast) if forecast else 1.0)
                actual = Decimal(str(round(forecast + noise, 2)))

            events.append(
                RawEconomicEvent(
                    country=country,
                    currency=currency,
                    event_name=event_name,
                    release_time=release_time,
                    source_name=self.name,
                    forecast=Decimal(str(forecast)),
                    previous=Decimal(str(previous)),
                    actual=actual,
                    unit=unit or None,
                )
            )

        return events

    def health_check(self) -> bool:
        return True

    def capabilities(self) -> EconomicCalendarProviderCapabilities:
        return _CAPABILITIES

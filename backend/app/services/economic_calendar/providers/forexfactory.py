"""ForexFactory weekly calendar feed (ADR-150).

The free alternative to Finnhub's calendar, which this project cannot
use: Finnhub returns 403 "You don't have access to this resource" on
`/api/v1/calendar/economic` without a paid plan, and had been doing so
on every 15-minute ingestion run since deploy, leaving `economic_events`
permanently empty.

Two properties of this feed shape the code below and are *not*
incidental:

- It publishes **one file, the current week**. There is no `lastweek`,
  `nextweek` or `thismonth` variant (all 404). So the pipeline's 7-day
  lookback / 30-day lookahead window can never be filled - `fetch_events`
  returns the intersection of the feed with the requested window and
  nothing more. Coverage is a rolling ~7 days.
- It carries **no `actual` values**, only `forecast` and `previous`.
  `surprise_calculator` therefore has nothing to compute from, and
  `EconomicEventEvidence` will have no surprise for these rows. The risk
  filter reads only `importance` and `risk_window`, so signal gating is
  unaffected.

The feed's own `impact` field is deliberately discarded. Importance is
this project's decision, derived from the event name by
`importance_scorer` (ADR-059), and taking it from a provider instead
would put a third party in charge of when we refuse to trade.
"""

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.services.economic_calendar.providers.base import (
    EconomicCalendarProviderCapabilities,
    RawEconomicEvent,
)
from app.services.economic_calendar.providers.exceptions import (
    PermanentEconomicCalendarProviderError,
    TransientEconomicCalendarProviderError,
)

#: One rolling week, both directions - the feed spans the current week,
#: so part of it is already past by the time it is fetched.
_CAPABILITIES = EconomicCalendarProviderCapabilities(
    supported_countries=frozenset({"US", "EU", "GB", "JP", "AU", "CA", "CH", "CN", "NZ"}),
    max_lookahead_days=7,
    max_lookback_days=7,
)

_FEED_PATH = "/ff_calendar_thisweek.json"

#: The feed's `country` field is really a currency code (docs/47 section 3
#: needs both). Inverted from `finnhub._COUNTRY_TO_CURRENCY` so the two
#: providers can never disagree about which country a currency belongs to.
_CURRENCY_TO_COUNTRY = {
    "USD": "US",
    "EUR": "EU",
    "GBP": "GB",
    "JPY": "JP",
    "AUD": "AU",
    "CAD": "CA",
    "CHF": "CH",
    "CNY": "CN",
    "NZD": "NZ",
}

#: Values arrive as display strings: "0.8%", "768B", "-1.2K", "117.9".
#: The magnitude suffix is kept as `unit` rather than multiplied out,
#: matching how `MockEconomicCalendarProvider` already emits ("K", 180.0)
#: - the number a trader sees on the release is the number we store.
_VALUE_PATTERN = re.compile(r"^(-?\d+(?:\.\d+)?)\s*([%KMBT])?$")


class ForexFactoryProvider:
    """`EconomicCalendarProvider` over ForexFactory's public weekly JSON.

    Needs no API key: the feed is the one ForexFactory publishes for its
    own site. That is also its risk - it is unversioned and carries no
    stability guarantee, so a shape change surfaces here as zero parsed
    events rather than as an error (ADR-150).
    """

    name = "forexfactory"

    def __init__(
        self,
        base_url: str,
        timeout: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """`transport` exists only so tests can inject
        `httpx.MockTransport`; production never passes it."""
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            # The feed is served by a CDN that refuses the default httpx
            # user agent.
            headers={"User-Agent": "ClaudeTradingAI/1.0"},
        )

    def fetch_events(self, start: datetime, end: datetime) -> list[RawEconomicEvent]:
        try:
            response = self._client.get(_FEED_PATH)
        except httpx.HTTPError as exc:
            raise TransientEconomicCalendarProviderError(f"forexfactory: {exc}") from exc

        if response.status_code >= 500:
            raise TransientEconomicCalendarProviderError(
                f"forexfactory: upstream returned {response.status_code}"
            )
        if response.status_code != 200:
            raise PermanentEconomicCalendarProviderError(
                f"forexfactory: unexpected status {response.status_code}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise TransientEconomicCalendarProviderError(
                f"forexfactory: invalid JSON response: {exc}"
            ) from exc

        if not isinstance(body, list):
            raise PermanentEconomicCalendarProviderError(
                "forexfactory: expected a JSON array of events"
            )

        return self._parse_events(body, start, end)

    def _parse_events(
        self, rows: list[Any], start: datetime, end: datetime
    ) -> list[RawEconomicEvent]:
        events: list[RawEconomicEvent] = []
        for row in rows:
            event = self._parse_event(row)
            # The feed is a fixed week; the caller asked for a window.
            # Returning only the intersection keeps the Protocol's
            # contract honest even though we cannot widen the feed.
            if event is not None and start <= event.release_time <= end:
                events.append(event)
        return events

    def _parse_event(self, row: Any) -> RawEconomicEvent | None:
        if not isinstance(row, dict):
            return None

        currency = str(row.get("country") or "").upper()
        # "All" marks global holidays and has no currency to attribute a
        # release to - `RawEconomicEvent` requires one.
        country = _CURRENCY_TO_COUNTRY.get(currency)
        title = row.get("title")
        raw_date = row.get("date")
        if country is None or not title or not raw_date:
            return None

        release_time = _parse_datetime(str(raw_date))
        if release_time is None:
            return None

        forecast, forecast_unit = _parse_value(row.get("forecast"))
        previous, previous_unit = _parse_value(row.get("previous"))

        return RawEconomicEvent(
            country=country,
            currency=currency,
            event_name=str(title),
            release_time=release_time,
            source_name=self.name,
            forecast=forecast,
            previous=previous,
            # No `actual` in this feed at all - see the module docstring.
            actual=None,
            unit=forecast_unit or previous_unit,
        )

    def health_check(self) -> bool:
        """Cheap liveness only - does not parse or validate the feed."""
        try:
            response = self._client.get(_FEED_PATH)
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    def capabilities(self) -> EconomicCalendarProviderCapabilities:
        return _CAPABILITIES

    def close(self) -> None:
        self._client.close()


def _parse_datetime(value: str) -> datetime | None:
    """The feed emits ISO 8601 with a US/Eastern offset
    (`2026-09-10T08:15:00-04:00`). Normalised to UTC so rows from this
    provider sort against every other source without a per-row offset."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _parse_value(value: object) -> tuple[Decimal | None, str | None]:
    """Split a display string into its number and magnitude/percent
    suffix. An empty string is the feed's way of saying "no figure
    published", which is `None` - never zero."""
    if not isinstance(value, str):
        return None, None

    match = _VALUE_PATTERN.match(value.strip().replace(",", ""))
    if match is None:
        return None, None

    try:
        number = Decimal(match.group(1))
    except InvalidOperation:
        return None, None

    return number, match.group(2)


__all__ = ["ForexFactoryProvider"]

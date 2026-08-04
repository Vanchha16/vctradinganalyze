from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import NoReturn

import httpx

from app.services.economic_calendar.providers.base import (
    EconomicCalendarProviderCapabilities,
    RawEconomicEvent,
)
from app.services.economic_calendar.providers.exceptions import (
    PermanentEconomicCalendarProviderError,
    TransientEconomicCalendarProviderError,
)
from app.services.economic_calendar.providers.finnhub_http import (
    FinnhubHttpClient,
    FinnhubTransportError,
)

_CAPABILITIES = EconomicCalendarProviderCapabilities(
    # Countries Finnhub's economic calendar reliably covers with a major-
    # currency mapping below - matches (and extends) MockEconomicCalendarProvider's set.
    supported_countries=frozenset({"US", "EU", "GB", "JP", "AU", "CA", "CH", "CN", "NZ"}),
    max_lookahead_days=30,
    max_lookback_days=30,
)

# Finnhub's economic calendar reports one currency-union country per
# release (docs/47 §3 needs a `currency`, Finnhub only gives `country`) -
# a small fixed mapping, not a guess: these are each country's sole legal
# tender relevant to the covered set.
_COUNTRY_TO_CURRENCY = {
    "US": "USD",
    "EU": "EUR",
    "GB": "GBP",
    "JP": "JPY",
    "AU": "AUD",
    "CA": "CAD",
    "CH": "CHF",
    "CN": "CNY",
    "NZ": "NZD",
}


class FinnhubAuthenticationError(PermanentEconomicCalendarProviderError):
    """Finnhub rejected the API key (401/403)."""


class FinnhubRateLimitedError(TransientEconomicCalendarProviderError):
    """Finnhub's own rate limit was hit (429)."""


def _parse_datetime(value: str) -> datetime:
    """Finnhub returns `YYYY-MM-DD HH:MM:SS` (UTC, no offset)."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


class FinnhubProvider:
    """Finnhub implementation of `EconomicCalendarProvider` (docs/47 §8)."""

    name = "finnhub"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = FinnhubHttpClient(
            base_url=base_url, api_key=api_key, timeout=timeout, transport=transport
        )

    def fetch_events(self, start: datetime, end: datetime) -> list[RawEconomicEvent]:
        params = {"from": start.strftime("%Y-%m-%d"), "to": end.strftime("%Y-%m-%d")}

        try:
            status_code, body = self._http.get("/api/v1/calendar/economic", params)
        except FinnhubTransportError as exc:
            raise TransientEconomicCalendarProviderError(f"finnhub: {exc}") from exc

        if status_code == 200 and "economicCalendar" in body:
            return self._parse_events(body)

        self._raise_for_error(status_code, body)

    def _parse_events(self, body: dict[str, object]) -> list[RawEconomicEvent]:
        raw_events = body.get("economicCalendar", [])
        if not isinstance(raw_events, list):
            raw_events = []

        events: list[RawEconomicEvent] = []
        for row in raw_events:
            country = str(row.get("country") or "")
            currency = _COUNTRY_TO_CURRENCY.get(country)
            event_name = row.get("event")
            release_time = row.get("time")
            if currency is None or not event_name or not release_time:
                continue

            events.append(
                RawEconomicEvent(
                    country=country,
                    currency=currency,
                    event_name=str(event_name),
                    release_time=_parse_datetime(str(release_time)),
                    source_name=self.name,
                    forecast=_to_decimal(row.get("estimate")),
                    previous=_to_decimal(row.get("prev")),
                    actual=_to_decimal(row.get("actual")),
                    unit=row.get("unit") or None,
                )
            )
        return events

    def _raise_for_error(self, status_code: int, body: dict[str, object]) -> NoReturn:
        message = str(body.get("error", f"HTTP {status_code}"))

        if status_code in (401, 403):
            raise FinnhubAuthenticationError(f"finnhub: {message}")
        if status_code == 429:
            raise FinnhubRateLimitedError(f"finnhub: {message}")
        if status_code >= 500:
            raise TransientEconomicCalendarProviderError(f"finnhub: {message}")
        raise PermanentEconomicCalendarProviderError(f"finnhub: {message}")

    def health_check(self) -> bool:
        try:
            status_code, body = self._http.get(
                "/api/v1/calendar/economic", {"from": "2024-01-01", "to": "2024-01-01"}
            )
        except FinnhubTransportError:
            return False
        return status_code == 200 and "economicCalendar" in body

    def capabilities(self) -> EconomicCalendarProviderCapabilities:
        return _CAPABILITIES

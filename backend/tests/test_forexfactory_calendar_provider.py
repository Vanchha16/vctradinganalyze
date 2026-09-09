"""ForexFactory economic calendar provider (ADR-150).

The feed shapes here are copied from a real response, not invented -
including the US/Eastern offset and the display-string forecasts, which
are the two things Finnhub did not have and the parser exists for.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from app.services.economic_calendar.providers.exceptions import (
    PermanentEconomicCalendarProviderError,
    TransientEconomicCalendarProviderError,
)
from app.services.economic_calendar.providers.forexfactory import ForexFactoryProvider

_ROW = {
    "title": "Core CPI m/m",
    "country": "USD",
    "date": "2026-09-11T08:30:00-04:00",
    "impact": "High",
    "forecast": "0.2%",
    "previous": "0.3%",
}

_WINDOW_START = datetime(2026, 9, 1, tzinfo=UTC)
_WINDOW_END = datetime(2026, 10, 1, tzinfo=UTC)


def _provider(handler: object) -> ForexFactoryProvider:
    return ForexFactoryProvider(
        base_url="https://feed.test",
        timeout=5.0,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )


def _responding(payload: object, status: int = 200) -> ForexFactoryProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=json.dumps(payload))

    return _provider(handler)


def test_fetch_events_parses_a_release() -> None:
    events = _responding([_ROW]).fetch_events(_WINDOW_START, _WINDOW_END)

    assert len(events) == 1
    event = events[0]
    assert event.event_name == "Core CPI m/m"
    assert event.currency == "USD"
    assert event.country == "US"
    assert event.source_name == "forexfactory"


def test_release_time_is_converted_from_eastern_to_utc() -> None:
    """The feed timestamps in US/Eastern. Storing the wall-clock time
    unchanged would put every US release four hours early, which is
    exactly the window `economic_filter` blocks trading in."""
    events = _responding([_ROW]).fetch_events(_WINDOW_START, _WINDOW_END)

    assert events[0].release_time == datetime(2026, 9, 11, 12, 30, tzinfo=UTC)


def test_display_values_split_into_a_number_and_a_unit() -> None:
    """Finnhub returned numbers; this feed returns "0.2%" and "205K".
    The suffix is kept as `unit` rather than multiplied out, so the
    stored figure is the one printed on the release."""
    rows = [
        {**_ROW, "forecast": "205K", "previous": "198K"},
        {**_ROW, "title": "Foreign Currency Reserves", "forecast": "", "previous": "768B"},
    ]

    events = _responding(rows).fetch_events(_WINDOW_START, _WINDOW_END)

    assert events[0].forecast == Decimal("205")
    assert events[0].unit == "K"
    # An empty forecast is "not published", never zero.
    assert events[1].forecast is None
    assert events[1].previous == Decimal("768")
    assert events[1].unit == "B"


def test_actual_is_always_none() -> None:
    """The weekly feed carries no released values at all - inferring one
    would feed `surprise_calculator` a number nobody published."""
    events = _responding([_ROW]).fetch_events(_WINDOW_START, _WINDOW_END)

    assert events[0].actual is None


def test_events_outside_the_requested_window_are_dropped() -> None:
    """The feed is a fixed week and ignores the window the caller asked
    for, so the provider applies it."""
    events = _responding([_ROW]).fetch_events(
        datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 9, 5, tzinfo=UTC)
    )

    assert events == []


def test_rows_without_a_mappable_currency_are_skipped() -> None:
    """ "All" marks a global holiday and belongs to no currency;
    `RawEconomicEvent` requires one."""
    rows = [{**_ROW, "country": "All", "title": "Bank Holiday"}, _ROW]

    events = _responding(rows).fetch_events(_WINDOW_START, _WINDOW_END)

    assert [e.event_name for e in events] == ["Core CPI m/m"]


def test_malformed_rows_are_skipped_without_losing_the_rest() -> None:
    """One bad row in a public feed must not cost a whole ingestion run
    - that is how the calendar goes empty again."""
    rows = [
        "not a dict",
        {**_ROW, "date": "not a date"},
        {**_ROW, "title": ""},
        {"country": "USD", "date": _ROW["date"]},
        _ROW,
    ]

    events = _responding(rows).fetch_events(_WINDOW_START, _WINDOW_END)

    assert len(events) == 1


def test_naive_timestamps_are_rejected_rather_than_assumed_utc() -> None:
    """A timestamp without an offset cannot be placed on the clock. This
    feed always carries one, so its absence means the shape changed."""
    events = _responding([{**_ROW, "date": "2026-09-11T08:30:00"}]).fetch_events(
        _WINDOW_START, _WINDOW_END
    )

    assert events == []


def test_server_error_is_transient() -> None:
    with pytest.raises(TransientEconomicCalendarProviderError):
        _responding([], status=503).fetch_events(_WINDOW_START, _WINDOW_END)


def test_client_error_is_permanent() -> None:
    """A 404 means the feed moved or was withdrawn - retrying every 15
    minutes will not bring it back."""
    with pytest.raises(PermanentEconomicCalendarProviderError):
        _responding([], status=404).fetch_events(_WINDOW_START, _WINDOW_END)


def test_a_non_array_body_is_permanent() -> None:
    with pytest.raises(PermanentEconomicCalendarProviderError):
        _responding({"error": "nope"}).fetch_events(_WINDOW_START, _WINDOW_END)


def test_invalid_json_is_transient() -> None:
    """A truncated body is usually a CDN hiccup, worth retrying."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="[{")

    with pytest.raises(TransientEconomicCalendarProviderError):
        _provider(handler).fetch_events(_WINDOW_START, _WINDOW_END)


def test_network_failure_is_transient() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(TransientEconomicCalendarProviderError):
        _provider(handler).fetch_events(_WINDOW_START, _WINDOW_END)


def test_health_check_reflects_feed_availability() -> None:
    assert _responding([]).health_check() is True
    assert _responding([], status=404).health_check() is False


def test_capabilities_declare_the_single_week_the_feed_actually_covers() -> None:
    """Only `ff_calendar_thisweek.json` exists - `nextweek`/`lastweek`
    are 404 - so claiming Finnhub's 30 days would be a lie the pipeline
    could act on."""
    capabilities = _responding([]).capabilities()

    assert capabilities.max_lookahead_days == 7
    assert capabilities.max_lookback_days == 7
    assert "US" in capabilities.supported_countries


def test_no_api_key_is_required() -> None:
    """The whole reason this provider exists: Finnhub's calendar is a
    paid resource and returned 403 forever."""
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, text="[]")

    _provider(handler).fetch_events(_WINDOW_START, _WINDOW_END)

    assert "token" not in sent[0].url.params
    assert "authorization" not in {k.lower() for k in sent[0].headers}


def test_fetch_uses_the_weekly_feed_path() -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, text="[]")

    _provider(handler).fetch_events(
        datetime.now(UTC) - timedelta(days=7), datetime.now(UTC) + timedelta(days=30)
    )

    assert sent[0].url.path == "/ff_calendar_thisweek.json"

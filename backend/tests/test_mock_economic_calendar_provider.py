from datetime import UTC, datetime, timedelta

from app.services.economic_calendar.providers.mock import MockEconomicCalendarProvider


def test_fetch_events_is_deterministic_for_same_window() -> None:
    provider = MockEconomicCalendarProvider()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=37)

    first = provider.fetch_events(start, end)
    second = provider.fetch_events(start, end)

    assert [(e.event_name, e.release_time) for e in first] == [
        (e.event_name, e.release_time) for e in second
    ]
    assert len(first) > 0


def test_fetch_events_release_times_are_within_window() -> None:
    provider = MockEconomicCalendarProvider()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=37)

    events = provider.fetch_events(start, end)

    assert all(start <= e.release_time <= end for e in events)


def test_fetch_events_spans_multiple_categories() -> None:
    provider = MockEconomicCalendarProvider()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=37)

    events = provider.fetch_events(start, end)
    names = {e.event_name for e in events}

    assert "CPI y/y" in names
    assert "Non-Farm Payrolls" in names
    assert "FOMC Interest Rate Decision" in names


def test_fetch_events_past_events_have_actual_future_events_do_not() -> None:
    provider = MockEconomicCalendarProvider()
    now = datetime.now(UTC)

    events = provider.fetch_events(now - timedelta(days=7), now + timedelta(days=30))

    past = [e for e in events if e.release_time <= now]
    future = [e for e in events if e.release_time > now]
    assert all(e.actual is not None for e in past)
    assert all(e.actual is None for e in future)


def test_health_check_always_true() -> None:
    assert MockEconomicCalendarProvider().health_check() is True


def test_capabilities_declare_supported_countries() -> None:
    capabilities = MockEconomicCalendarProvider().capabilities()
    assert "US" in capabilities.supported_countries

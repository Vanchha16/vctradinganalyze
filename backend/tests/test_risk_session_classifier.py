from datetime import UTC, datetime

from app.services.risk_management.session_classifier import classify
from app.services.risk_management.types import MarketSession

# 2026-01-05 is a Monday; 2026-01-02 is a Friday; 2026-01-03 Saturday; 2026-01-04 Sunday.
_MONDAY = datetime(2026, 1, 5, tzinfo=UTC)
_FRIDAY = datetime(2026, 1, 2, tzinfo=UTC)
_SATURDAY = datetime(2026, 1, 3, tzinfo=UTC)
_SUNDAY = datetime(2026, 1, 4, tzinfo=UTC)


def test_classify_asian_session() -> None:
    assert classify(_MONDAY.replace(hour=2)) == MarketSession.ASIAN


def test_classify_london_session() -> None:
    assert classify(_MONDAY.replace(hour=10)) == MarketSession.LONDON


def test_classify_new_york_session() -> None:
    assert classify(_MONDAY.replace(hour=19)) == MarketSession.NEW_YORK


def test_classify_london_new_york_overlap() -> None:
    assert classify(_MONDAY.replace(hour=14)) == MarketSession.LONDON_NEW_YORK_OVERLAP


def test_classify_sydney_session() -> None:
    assert classify(_MONDAY.replace(hour=23)) == MarketSession.SYDNEY


def test_classify_asian_wins_over_sydney_for_overlapping_early_hours() -> None:
    """Sydney's 22:00-07:00 wrap and Asian's 00:00-09:00 overlap for
    hours 00-06 - Asian is checked first and wins for that overlap."""
    assert classify(_MONDAY.replace(hour=5)) == MarketSession.ASIAN


def test_classify_closed_on_saturday() -> None:
    assert classify(_SATURDAY.replace(hour=12)) == MarketSession.CLOSED


def test_classify_closed_sunday_before_reopen() -> None:
    assert classify(_SUNDAY.replace(hour=21)) == MarketSession.CLOSED


def test_classify_open_sunday_after_reopen() -> None:
    assert classify(_SUNDAY.replace(hour=22)) != MarketSession.CLOSED


def test_classify_closed_friday_after_close() -> None:
    assert classify(_FRIDAY.replace(hour=22)) == MarketSession.CLOSED


def test_classify_open_friday_before_close() -> None:
    assert classify(_FRIDAY.replace(hour=21)) != MarketSession.CLOSED


def test_classify_covers_every_hour_on_a_weekday() -> None:
    for hour in range(24):
        assert classify(_MONDAY.replace(hour=hour)) != MarketSession.CLOSED

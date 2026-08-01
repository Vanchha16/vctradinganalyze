from datetime import UTC, datetime, timedelta

from app.models.enums import EconomicEventImportance
from app.services.economic_calendar.risk_window import is_in_risk_window

_RELEASE = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_critical_is_in_window_30_minutes_before() -> None:
    now = _RELEASE - timedelta(minutes=30)
    assert is_in_risk_window(now, _RELEASE, EconomicEventImportance.CRITICAL) is True


def test_critical_is_in_window_30_minutes_after() -> None:
    now = _RELEASE + timedelta(minutes=30)
    assert is_in_risk_window(now, _RELEASE, EconomicEventImportance.CRITICAL) is True


def test_critical_is_not_in_window_31_minutes_before() -> None:
    now = _RELEASE - timedelta(minutes=31)
    assert is_in_risk_window(now, _RELEASE, EconomicEventImportance.CRITICAL) is False


def test_critical_is_not_in_window_31_minutes_after() -> None:
    now = _RELEASE + timedelta(minutes=31)
    assert is_in_risk_window(now, _RELEASE, EconomicEventImportance.CRITICAL) is False


def test_high_is_in_window_60_minutes_before() -> None:
    now = _RELEASE - timedelta(minutes=60)
    assert is_in_risk_window(now, _RELEASE, EconomicEventImportance.HIGH) is True


def test_high_is_in_window_at_release_time() -> None:
    assert is_in_risk_window(_RELEASE, _RELEASE, EconomicEventImportance.HIGH) is True


def test_high_is_not_in_window_61_minutes_before() -> None:
    now = _RELEASE - timedelta(minutes=61)
    assert is_in_risk_window(now, _RELEASE, EconomicEventImportance.HIGH) is False


def test_high_is_not_in_window_after_release() -> None:
    """docs/14 §8: High-impact risk window is before-only, unlike
    Critical's symmetric before/after window."""
    now = _RELEASE + timedelta(minutes=1)
    assert is_in_risk_window(now, _RELEASE, EconomicEventImportance.HIGH) is False


def test_medium_is_never_in_risk_window() -> None:
    assert is_in_risk_window(_RELEASE, _RELEASE, EconomicEventImportance.MEDIUM) is False


def test_low_is_never_in_risk_window() -> None:
    assert is_in_risk_window(_RELEASE, _RELEASE, EconomicEventImportance.LOW) is False


def test_handles_naive_datetimes_from_sqlite() -> None:
    """SQLite returns naive datetimes for `DateTime(timezone=True)`
    columns even when written UTC-aware (BACKLOG.md §9) - must not raise."""
    naive_release = _RELEASE.replace(tzinfo=None)
    naive_now = (_RELEASE - timedelta(minutes=10)).replace(tzinfo=None)
    assert is_in_risk_window(naive_now, naive_release, EconomicEventImportance.CRITICAL) is True

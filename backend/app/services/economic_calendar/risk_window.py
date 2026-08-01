"""Deterministic, read-time-only risk window (docs/14 §8, docs/47 §7,
ADR-061). Pure function - never persisted. A stored boolean would be
correct only at the instant it was computed and stale immediately after,
since this is a function of continuously-advancing wall-clock time."""

from datetime import UTC, datetime, timedelta

from app.models.enums import EconomicEventImportance

_CRITICAL_WINDOW = timedelta(minutes=30)
_HIGH_WINDOW_BEFORE = timedelta(minutes=60)


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes for `DateTime(timezone=True)`
    columns even though they were written UTC-aware (BACKLOG.md §9) -
    mirrors `analysis_confidence.freshness_analyzer._as_aware_utc`."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def is_in_risk_window(
    now: datetime, release_time: datetime, importance: EconomicEventImportance
) -> bool:
    now = _as_aware_utc(now)
    release_time = _as_aware_utc(release_time)
    delta = release_time - now  # positive: event is upcoming; negative: event has passed

    if importance is EconomicEventImportance.CRITICAL:
        return -_CRITICAL_WINDOW <= delta <= _CRITICAL_WINDOW
    if importance is EconomicEventImportance.HIGH:
        return timedelta(0) <= delta <= _HIGH_WINDOW_BEFORE
    return False

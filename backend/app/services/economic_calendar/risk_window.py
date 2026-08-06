"""Deterministic, read-time-only risk window (docs/14 §8, docs/47 §7,
ADR-061). Pure function - never persisted. A stored boolean would be
correct only at the instant it was computed and stale immediately after,
since this is a function of continuously-advancing wall-clock time."""

from datetime import datetime, timedelta

from app.models.enums import EconomicEventImportance
from app.utils.time import as_aware_utc

_CRITICAL_WINDOW = timedelta(minutes=30)
_HIGH_WINDOW_BEFORE = timedelta(minutes=60)


def is_in_risk_window(
    now: datetime, release_time: datetime, importance: EconomicEventImportance
) -> bool:
    now = as_aware_utc(now)
    release_time = as_aware_utc(release_time)
    delta = release_time - now  # positive: event is upcoming; negative: event has passed

    if importance is EconomicEventImportance.CRITICAL:
        return -_CRITICAL_WINDOW <= delta <= _CRITICAL_WINDOW
    if importance is EconomicEventImportance.HIGH:
        return timedelta(0) <= delta <= _HIGH_WINDOW_BEFORE
    return False

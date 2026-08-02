"""Deterministic, read-time-only signal status (docs/51 §4/§5, ADR-088).
Pure function - never persisted. Mirrors
`economic_calendar/risk_window.py`'s reasoning exactly: EXPIRED is a
function of continuously-advancing wall-clock time, correct only at the
instant it's computed and stale immediately after, so it must never be
written back to the row."""

from datetime import UTC, datetime, timedelta

from app.config import settings
from app.models.enums import SignalStatus


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes for `DateTime(timezone=True)`
    columns even though they were written UTC-aware (BACKLOG.md §9) -
    mirrors `analysis_confidence.freshness_analyzer._as_aware_utc`."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def effective_status(
    stored_status: SignalStatus, created_at: datetime, now: datetime
) -> SignalStatus:
    """Phase 6B only ever writes ACTIVE (ADR-088) - every other stored
    value (reserved for a future phase's live-monitoring work) passes
    through unchanged. ACTIVE becomes EXPIRED once `signal_ttl_hours`
    has elapsed since `created_at`, computed here rather than stored."""
    if stored_status is not SignalStatus.ACTIVE:
        return stored_status

    created_at = _as_aware_utc(created_at)
    now = _as_aware_utc(now)
    if now - created_at >= timedelta(hours=settings.signal_ttl_hours):
        return SignalStatus.EXPIRED
    return SignalStatus.ACTIVE

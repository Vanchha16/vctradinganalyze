from datetime import UTC, datetime, timedelta

from app.models.enums import SignalStatus
from app.services.signal import status_resolver

_CREATED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_active_within_ttl_stays_active() -> None:
    now = _CREATED_AT + timedelta(hours=23)
    assert status_resolver.effective_status(SignalStatus.ACTIVE, _CREATED_AT, now) is (
        SignalStatus.ACTIVE
    )


def test_active_past_ttl_becomes_expired() -> None:
    now = _CREATED_AT + timedelta(hours=24)
    assert status_resolver.effective_status(SignalStatus.ACTIVE, _CREATED_AT, now) is (
        SignalStatus.EXPIRED
    )


def test_active_well_past_ttl_becomes_expired() -> None:
    now = _CREATED_AT + timedelta(days=10)
    assert status_resolver.effective_status(SignalStatus.ACTIVE, _CREATED_AT, now) is (
        SignalStatus.EXPIRED
    )


def test_non_active_stored_status_passes_through_unchanged() -> None:
    """Phase 6B never writes anything but ACTIVE (ADR-088), but the
    resolver must not reinterpret a future phase's stored states."""
    now = _CREATED_AT + timedelta(days=10)
    for status in (
        SignalStatus.DRAFT,
        SignalStatus.TRIGGERED,
        SignalStatus.CANCELLED,
        SignalStatus.CLOSED,
        SignalStatus.SUCCESSFUL,
        SignalStatus.STOPPED_OUT,
    ):
        assert status_resolver.effective_status(status, _CREATED_AT, now) is status


def test_handles_naive_datetimes_from_sqlite() -> None:
    """SQLite returns naive datetimes for `DateTime(timezone=True)`
    columns even when written UTC-aware (BACKLOG.md §9) - must not raise."""
    naive_created_at = _CREATED_AT.replace(tzinfo=None)
    naive_now = (_CREATED_AT + timedelta(hours=1)).replace(tzinfo=None)
    result = status_resolver.effective_status(SignalStatus.ACTIVE, naive_created_at, naive_now)
    assert result is SignalStatus.ACTIVE

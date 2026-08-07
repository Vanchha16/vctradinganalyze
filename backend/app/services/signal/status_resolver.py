"""Deterministic, read-time-only signal status (docs/51 §4/§5, ADR-088,
extended by ADR-137). Pure function - never persisted. Mirrors
`economic_calendar/risk_window.py`'s reasoning exactly: EXPIRED/CLOSED-
by-TTL are each a function of continuously-advancing wall-clock time,
correct only at the instant computed and stale immediately after, so
neither is ever written back to the row."""

from datetime import datetime, timedelta

from app.config import settings
from app.models.enums import SignalStatus
from app.utils.time import as_aware_utc


def effective_status(
    stored_status: SignalStatus,
    created_at: datetime,
    now: datetime,
    *,
    triggered_at: datetime | None = None,
) -> SignalStatus:
    """ACTIVE becomes EXPIRED once `signal_ttl_hours` has elapsed since
    `created_at` (ADR-088) - a pending order that never filled, no P&L.

    TRIGGERED becomes CLOSED once `signal_triggered_ttl_hours` has
    elapsed since `triggered_at` (ADR-137, §3.4) - a live trade that
    never reached TP or SL. Same read-time-only treatment as EXPIRED:
    not persisted, `profit_loss` stays null. `triggered_at` is required
    to make this determination; callers that don't have it (e.g. a
    signal that was never triggered) simply omit it and TRIGGERED
    passes through unchanged, same as every other non-ACTIVE status.

    Every other stored value passes through unchanged."""
    now = as_aware_utc(now)

    if stored_status is SignalStatus.ACTIVE:
        if now - as_aware_utc(created_at) >= timedelta(hours=settings.signal_ttl_hours):
            return SignalStatus.EXPIRED
        return SignalStatus.ACTIVE

    if stored_status is SignalStatus.TRIGGERED and triggered_at is not None:
        if now - as_aware_utc(triggered_at) >= timedelta(hours=settings.signal_triggered_ttl_hours):
            return SignalStatus.CLOSED
        return SignalStatus.TRIGGERED

    return stored_status

from enum import StrEnum


class SignalStatus(StrEnum):
    """docs/11_SIGNAL_ENGINE.md §18, docs/51 §4 (ADR-088, extended by
    ADR-137). Phase 6B only ever wrote ACTIVE and only ever computed
    EXPIRED (read-time only). Phase 9E's monitoring task
    (`workers/signal_monitoring_tasks.py`) now also writes TRIGGERED,
    SUCCESSFUL, and STOPPED_OUT, and computes CLOSED read-time-only
    (same treatment as EXPIRED, via `status_resolver.effective_status`).
    DRAFT and CANCELLED remain unreachable through any current code path.
    """

    DRAFT = "draft"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    CLOSED = "closed"
    SUCCESSFUL = "successful"
    STOPPED_OUT = "stopped_out"

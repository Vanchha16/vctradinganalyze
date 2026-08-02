from enum import StrEnum


class SignalStatus(StrEnum):
    """docs/11_SIGNAL_ENGINE.md §18, docs/51 §4 (ADR-088). Phase 6B only
    ever writes ACTIVE and only ever computes EXPIRED (read-time only,
    via `app.services.signal.status_resolver`, never persisted). The
    remaining five states are reserved for a future phase that builds
    live price-monitoring / trigger detection / outcome tracking - not
    reachable through any Phase 6B code path.
    """

    DRAFT = "draft"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    CLOSED = "closed"
    SUCCESSFUL = "successful"
    STOPPED_OUT = "stopped_out"

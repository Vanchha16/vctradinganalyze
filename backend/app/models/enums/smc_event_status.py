from enum import StrEnum


class SMCEventStatus(StrEnum):
    """Lifecycle states for a persisted SMC event (ADR-037).

    Allowed transitions:
        ACTIVE -> MITIGATED
        ACTIVE -> INVALIDATED
        MITIGATED -> ARCHIVED
        INVALIDATED -> ARCHIVED

    ARCHIVED is terminal. Rows are never deleted - archiving is a status
    change, not a removal, so historical SMC events remain queryable.
    """

    ACTIVE = "active"
    MITIGATED = "mitigated"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"

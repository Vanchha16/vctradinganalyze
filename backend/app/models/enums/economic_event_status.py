from enum import StrEnum


class EconomicEventStatus(StrEnum):
    """Economic event lifecycle status (docs/47 §2, ADR-058)."""

    SCHEDULED = "scheduled"
    RELEASED = "released"
    REVISED = "revised"
    CANCELLED = "cancelled"

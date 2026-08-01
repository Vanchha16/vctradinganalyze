from enum import StrEnum


class EconomicEventImportance(StrEnum):
    """Economic event importance (docs/14_ECONOMIC_CALENDAR_ENGINE.md §4).
    Distinct from `NewsImportance` (ADR-059/ADR-048) - this domain's
    scoring has no source-tier axis."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

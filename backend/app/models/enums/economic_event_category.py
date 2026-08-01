from enum import StrEnum


class EconomicEventCategory(StrEnum):
    """Economic event category (docs/14_ECONOMIC_CALENDAR_ENGINE.md §3)."""

    INFLATION = "inflation"
    EMPLOYMENT = "employment"
    GROWTH = "growth"
    CENTRAL_BANK = "central_bank"
    CONSUMER = "consumer"
    HOUSING = "housing"
    OTHER = "other"

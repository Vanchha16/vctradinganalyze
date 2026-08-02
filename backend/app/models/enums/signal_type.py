from enum import StrEnum


class SignalType(StrEnum):
    """docs/11_SIGNAL_ENGINE.md §16, docs/51 §2 (ADR-086). A `Signal` row
    is only ever created for an actionable BUY/SELL trade call - a WAIT
    `Recommendation` produces no `Signal` row at all, so this enum never
    needs a WAIT member."""

    BUY = "buy"
    SELL = "sell"

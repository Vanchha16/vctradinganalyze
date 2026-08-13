from enum import StrEnum


class OrderStatus(StrEnum):
    """Lifecycle of a real broker order placed via the execution bridge
    (.claude/specs/phase-11-ea-bot-exness-mt5-execution.md §3B/§6).

    Mirrors the bridge's own pending-order -> filled/cancelled/rejected
    shape, kept deliberately separate from `SignalStatus` (§1 of the
    spec) - a `Signal` is "what was recommended," a `BrokerOrder` is
    "what actually happened on the real account for that recommendation."
    """

    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    CLOSED = "closed"

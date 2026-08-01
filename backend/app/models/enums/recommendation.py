from enum import StrEnum


class Recommendation(StrEnum):
    """docs/07_AI_ORCHESTRATOR.md §5, docs/13_AI_REASONING_ENGINE.md §6.
    Computed deterministically by `recommendation_decision.py` - never by
    the AI (ADR-078)."""

    BUY = "buy"
    SELL = "sell"
    WAIT = "wait"

from enum import StrEnum


class ConversationStatus(StrEnum):
    """docs/52 §6/§8 (ADR-097). `ARCHIVED` is soft (reversible in
    principle); a genuinely removed conversation is a hard delete
    instead, not a third status."""

    ACTIVE = "active"
    ARCHIVED = "archived"

from enum import StrEnum


class NewsImportance(StrEnum):
    """News importance level (docs/10_NEWS_SENTIMENT_ENGINE.md §8)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    IGNORE = "ignore"

from enum import StrEnum


class NewsSourceTier(StrEnum):
    """Source credibility tier (docs/10_NEWS_SENTIMENT_ENGINE.md §3)."""

    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"

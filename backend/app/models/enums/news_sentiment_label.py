from enum import StrEnum


class NewsSentimentLabel(StrEnum):
    """News sentiment (docs/10_NEWS_SENTIMENT_ENGINE.md §7). Deterministic
    lexicon-scored (ADR-051) - never a free-text/asset-qualified variant."""

    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"

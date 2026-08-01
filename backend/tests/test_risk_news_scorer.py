from datetime import UTC, datetime
from uuid import uuid4

from app.models.enums import NewsCategory, NewsImportance, NewsSentimentLabel
from app.services.news_sentiment.types import NewsSentimentEvidence
from app.services.risk_management.news_scorer import score
from app.services.risk_management.types import TradeDirection

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _article(sentiment: NewsSentimentLabel, confidence: float = 80.0) -> NewsSentimentEvidence:
    return NewsSentimentEvidence(
        article_id=uuid4(),
        headline="Some headline",
        category=NewsCategory.INFLATION,
        importance=NewsImportance.HIGH,
        sentiment=sentiment,
        confidence=confidence,
        reason="test",
        affected_assets=["EURUSD"],
        ai_summary=None,
        published_at=_NOW,
        source="mock",
    )


def test_score_neutral_when_no_articles() -> None:
    assert score([], TradeDirection.LONG) == 5.0


def test_score_boosted_when_bullish_agrees_with_long() -> None:
    articles = [_article(NewsSentimentLabel.BULLISH, confidence=100.0)]
    result = score(articles, TradeDirection.LONG)
    assert result > 5.0


def test_score_reduced_when_bullish_opposes_short() -> None:
    articles = [_article(NewsSentimentLabel.BULLISH, confidence=100.0)]
    result = score(articles, TradeDirection.SHORT)
    assert result < 5.0


def test_score_boosted_when_bearish_agrees_with_short() -> None:
    articles = [_article(NewsSentimentLabel.BEARISH, confidence=100.0)]
    result = score(articles, TradeDirection.SHORT)
    assert result > 5.0


def test_score_neutral_article_stays_at_baseline() -> None:
    articles = [_article(NewsSentimentLabel.NEUTRAL, confidence=100.0)]
    assert score(articles, TradeDirection.LONG) == 5.0


def test_score_clamped_between_0_and_10() -> None:
    articles = [_article(NewsSentimentLabel.VERY_BEARISH, confidence=100.0)] * 5
    result = score(articles, TradeDirection.LONG)
    assert 0.0 <= result <= 10.0

from app.models.enums import NewsSentimentLabel
from app.services.news_sentiment.sentiment_scorer import score
from tests.news_sentiment_helpers import make_raw_article


def test_score_neutral_when_no_keywords_match() -> None:
    article = make_raw_article(title="Company Reports Results", summary="Nothing notable.")
    label, confidence, reason = score(article)
    assert label == NewsSentimentLabel.NEUTRAL
    assert confidence == 50.0
    assert "No sentiment-bearing keywords" in reason


def test_score_bullish_for_positive_keywords() -> None:
    article = make_raw_article(
        title="Retail Sales Beat Expectations, Consumer Confidence Improves", summary=None
    )
    label, confidence, _ = score(article)
    assert label in (NewsSentimentLabel.BULLISH, NewsSentimentLabel.VERY_BULLISH)
    assert confidence > 50.0


def test_score_very_bearish_for_strongly_negative_keywords() -> None:
    article = make_raw_article(
        title="Recession Fears Resurface as Markets Crash and Collapse", summary=None
    )
    label, confidence, _ = score(article)
    assert label == NewsSentimentLabel.VERY_BEARISH
    assert confidence > 50.0


def test_score_confidence_capped_at_100() -> None:
    article = make_raw_article(
        title=(
            "Recession Fears Resurface as Markets Crash and Collapse Amid War, Tensions, "
            "Slowdown, Slide, Falls, Slows"
        ),
        summary=None,
    )
    _, confidence, _ = score(article)
    assert confidence <= 100.0


def test_score_reason_lists_matched_keywords() -> None:
    article = make_raw_article(title="Gold Prices Slide as Dollar Strengthens", summary=None)
    _, _, reason = score(article)
    assert "slide" in reason

"""Deterministic lexicon-based sentiment scoring (docs/10 §7, docs/46 §5,
ADR-051). A hand-built financial polarity table - no ML/LLM is used for
the sentiment label or confidence; AI is reserved solely for the
narrative summary (`ai_summary_generator.py`)."""

from app.models.enums import NewsSentimentLabel
from app.services.news.providers.base import RawNewsArticle

# Signed keyword weights - positive skews bullish, negative skews bearish.
# Starting-point values, not tuned against real outcomes (same caveat as
# every prior scoring ADR: 028/030/035/036/037/042/046).
_POLARITY_LEXICON: dict[str, float] = {
    "beats expectations": 2.0,
    "beat forecast": 2.0,
    "stronger than forecast": 2.0,
    "rallies": 2.0,
    "rally": 2.0,
    "surge": 2.0,
    "surges": 2.0,
    "improves": 1.0,
    "strengthens": 1.0,
    "record high": 2.0,
    "outperform": 1.0,
    "renewed institutional buying": 1.0,
    "growth": 1.0,
    "rate hike": -2.0,
    "tightening": -1.0,
    "recession": -3.0,
    "weaker than forecast": -2.0,
    "misses expectations": -2.0,
    "miss forecast": -2.0,
    "slide": -1.0,
    "slides": -1.0,
    "falls": -1.0,
    "slows": -1.0,
    "slowdown": -1.0,
    "tension": -1.0,
    "tensions": -1.0,
    "collapse": -3.0,
    "crash": -3.0,
    "war": -2.0,
    "recession fears": -2.0,
}

_BAND_THRESHOLDS: list[tuple[float, NewsSentimentLabel]] = [
    (3.0, NewsSentimentLabel.VERY_BULLISH),
    (1.0, NewsSentimentLabel.BULLISH),
    (-0.999, NewsSentimentLabel.NEUTRAL),
    (-2.999, NewsSentimentLabel.BEARISH),
]
_DEFAULT_BAND = NewsSentimentLabel.VERY_BEARISH


def _article_text(article: RawNewsArticle) -> str:
    return f"{article.title} {article.summary or ''}".lower()


def _matched_keywords(text: str) -> list[tuple[str, float]]:
    return [(keyword, weight) for keyword, weight in _POLARITY_LEXICON.items() if keyword in text]


def _band_for(raw_score: float) -> NewsSentimentLabel:
    for threshold, label in _BAND_THRESHOLDS:
        if raw_score >= threshold:
            return label
    return _DEFAULT_BAND


def score(article: RawNewsArticle) -> tuple[NewsSentimentLabel, float, str]:
    """Returns (sentiment_label, confidence 0-100, reason)."""
    text = _article_text(article)
    matches = _matched_keywords(text)
    raw_score = sum(weight for _, weight in matches)
    label = _band_for(raw_score)

    if not matches:
        return NewsSentimentLabel.NEUTRAL, 50.0, "No sentiment-bearing keywords matched."

    confidence = min(100.0, 50.0 + abs(raw_score) * 10.0 + len(matches) * 5.0)
    matched_terms = ", ".join(keyword for keyword, _ in matches)
    reason = (
        f"Matched {len(matches)} sentiment keyword(s): {matched_terms} "
        f"(score={raw_score:+.1f})."
    )
    return label, confidence, reason

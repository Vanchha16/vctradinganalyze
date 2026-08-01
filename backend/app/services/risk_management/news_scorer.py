"""Deterministic News Score derivation (docs/12 §3/§15). Reuses
`NewsSentimentEvidence` (Phase 5A) directly - no new sentiment analysis.
Neutral baseline (5/10) when no recent news exists; scaled toward 10 when
recent sentiment agrees with the candidate trade's direction, toward 0
when it opposes."""

from collections.abc import Sequence

from app.models.enums import NewsSentimentLabel
from app.services.news_sentiment.types import NewsSentimentEvidence
from app.services.risk_management.types import TradeDirection

_NEUTRAL_SCORE = 5.0
_MAX_ADJUSTMENT = 5.0

_BULLISH_LABELS = frozenset({NewsSentimentLabel.BULLISH, NewsSentimentLabel.VERY_BULLISH})
_BEARISH_LABELS = frozenset({NewsSentimentLabel.BEARISH, NewsSentimentLabel.VERY_BEARISH})


def score(articles: Sequence[NewsSentimentEvidence], direction: TradeDirection) -> float:
    if not articles:
        return _NEUTRAL_SCORE

    contributions: list[float] = []
    for article in articles:
        confidence_weight = article.confidence / 100
        if article.sentiment in _BULLISH_LABELS:
            agrees = direction is TradeDirection.LONG
        elif article.sentiment in _BEARISH_LABELS:
            agrees = direction is TradeDirection.SHORT
        else:
            contributions.append(_NEUTRAL_SCORE)
            continue

        adjustment = _MAX_ADJUSTMENT * confidence_weight
        contributions.append(_NEUTRAL_SCORE + adjustment if agrees else _NEUTRAL_SCORE - adjustment)

    average = sum(contributions) / len(contributions)
    return max(0.0, min(10.0, average))

"""Aggregates the deterministic analyzers into one `RawArticleClassification`
per candidate article (docs/46 §3/§5) - analogous to
`app.services.analysis_confidence.confidence_aggregator.combine`, but for
News Sentiment's classify/score/detect pipeline rather than a weighted sum.
"""

from collections.abc import Sequence

from app.models.asset import Asset
from app.models.enums import NewsSourceTier
from app.services.news.providers.base import RawNewsArticle
from app.services.news_sentiment import category_classifier, importance_scorer, sentiment_scorer
from app.services.news_sentiment.asset_detector import detect as detect_assets
from app.services.news_sentiment.types import RawArticleClassification


def aggregate(
    article: RawNewsArticle,
    *,
    source_tier: NewsSourceTier,
    known_assets: Sequence[Asset],
) -> RawArticleClassification:
    category = category_classifier.classify(article)
    importance = importance_scorer.score(category, source_tier)
    sentiment, confidence, reason = sentiment_scorer.score(article)
    text = f"{article.title} {article.summary or ''}"
    affected_assets = detect_assets(text, known_assets)

    return RawArticleClassification(
        category=category,
        importance=importance,
        sentiment=sentiment,
        confidence=confidence,
        reason=reason,
        affected_assets=affected_assets,
    )

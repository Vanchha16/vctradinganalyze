"""Read-path orchestrator for the News Sentiment Engine (docs/46 §1/§3).

Unlike Technical Analysis/SMC/Market Regime/Confidence, this engine never
calls a provider or recomputes evidence - it queries already-persisted
`NewsSentiment` rows (written by `NewsIngestionPipeline`, the separate
write-path orchestrator). See docs/46 §10 for why this engine has no
`timeframe` parameter.
"""

from datetime import UTC, datetime

from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.services.news_sentiment.types import NewsSentimentEvidence, NewsSentimentResult


class NewsSentimentEngine:
    def __init__(self, sentiment_repository: NewsSentimentRepository) -> None:
        self._sentiment_repository = sentiment_repository

    def get_sentiment_for_asset(self, symbol: str, since: datetime) -> NewsSentimentResult:
        rows = self._sentiment_repository.find_by_asset_since(symbol, since)

        articles = [
            NewsSentimentEvidence(
                article_id=row.id,
                headline=row.article.title,
                category=row.article.category,
                importance=row.article.importance,
                sentiment=row.sentiment,
                confidence=row.confidence,
                reason=row.reason,
                affected_assets=row.affected_assets,
                ai_summary=row.ai_summary,
                published_at=row.article.published_at,
                source=row.article.source.name,
            )
            for row in rows
        ]

        return NewsSentimentResult(
            symbol=symbol,
            since=since,
            calculated_at=datetime.now(UTC),
            articles=articles,
            warnings=[],
        )

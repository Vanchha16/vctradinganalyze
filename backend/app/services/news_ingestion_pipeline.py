"""Write-path orchestrator for the News Sentiment Engine (docs/46 §3),
Celery-triggered rather than API-triggered. Kept separate from
`NewsSentimentEngine` (the read-path) since ingestion is a scheduled
producer concern, not an on-demand query (docs/46 §3).

Fetch -> dedup -> classify/score/detect -> (optional) AI summary ->
persist. Never blocks on the AI summary call - a failure there degrades
to `ai_summary=None`, every other field is populated normally.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.models.enums import NewsSourceTier
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.repositories.asset_repository import AssetRepository
from app.repositories.news_article_repository import NewsArticleRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.services.news.providers.base import NewsProvider
from app.services.news.providers.exceptions import NewsProviderError
from app.services.news_sentiment import dedup_detector, scoring_engine
from app.services.news_sentiment.ai_summary_generator import AISummaryGenerator

logger = logging.getLogger(__name__)

# Known outlets' credibility tier (docs/10 §3). Unrecognized sources
# default to TIER_3 - a conservative floor rather than an invented tier.
_KNOWN_SOURCE_TIERS: dict[str, NewsSourceTier] = {
    "Reuters": NewsSourceTier.TIER_1,
    "Bloomberg": NewsSourceTier.TIER_1,
    "Associated Press": NewsSourceTier.TIER_1,
    "Forex Factory": NewsSourceTier.TIER_2,
    "Investing.com": NewsSourceTier.TIER_2,
    "Trading Economics": NewsSourceTier.TIER_2,
    "CoinDesk": NewsSourceTier.TIER_2,
    "CoinTelegraph": NewsSourceTier.TIER_2,
}
_DEFAULT_SOURCE_TIER = NewsSourceTier.TIER_3


class NewsIngestionPipeline:
    def __init__(
        self,
        *,
        providers: list[NewsProvider],
        source_repository: NewsSourceRepository,
        article_repository: NewsArticleRepository,
        sentiment_repository: NewsSentimentRepository,
        asset_repository: AssetRepository,
        ai_summary_generator: AISummaryGenerator,
    ) -> None:
        self._providers = providers
        self._source_repository = source_repository
        self._article_repository = article_repository
        self._sentiment_repository = sentiment_repository
        self._asset_repository = asset_repository
        self._ai_summary_generator = ai_summary_generator

    def run(self, since: datetime) -> int:
        """Ingests articles published since `since`. Returns the number of
        new articles persisted (duplicates are skipped, not counted)."""
        known_assets = self._asset_repository.list_active(limit=1000)
        existing_articles = self._article_repository.find_recent(since=since)
        ingested = 0

        for provider in self._providers:
            try:
                raw_articles = provider.fetch_latest(since)
            except NewsProviderError as exc:
                logger.warning("News provider %s failed: %s", provider.name, exc)
                continue

            for raw_article in raw_articles:
                if dedup_detector.is_duplicate(raw_article, existing_articles):
                    continue

                source = self._get_or_create_source(raw_article.source_name)
                classification = scoring_engine.aggregate(
                    raw_article, source_tier=source.tier, known_assets=known_assets
                )
                ai_summary = self._ai_summary_generator.generate(raw_article, classification)

                article = self._article_repository.create(
                    NewsArticle(
                        source_id=source.id,
                        title=raw_article.title,
                        summary=raw_article.summary,
                        content=raw_article.content,
                        url=raw_article.url,
                        category=classification.category,
                        language=raw_article.language,
                        importance=classification.importance,
                        published_at=raw_article.published_at,
                    )
                )
                self._sentiment_repository.create(
                    NewsSentiment(
                        article_id=article.id,
                        sentiment=classification.sentiment,
                        confidence=classification.confidence,
                        reason=classification.reason,
                        affected_assets=classification.affected_assets,
                        ai_summary=ai_summary,
                    )
                )

                existing_articles = [*existing_articles, article]
                ingested += 1

        self._source_repository.commit()
        return ingested

    def _get_or_create_source(self, name: str) -> NewsSource:
        source = self._source_repository.find_by_name(name)
        if source is not None:
            return source
        return self._source_repository.create(
            NewsSource(
                name=name,
                website="",
                tier=_KNOWN_SOURCE_TIERS.get(name, _DEFAULT_SOURCE_TIER),
                priority=0,
                is_active=True,
            )
        )


def default_since(lookback_hours: int) -> datetime:
    return datetime.now(UTC) - timedelta(hours=lookback_hours)

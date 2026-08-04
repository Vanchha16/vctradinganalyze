from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies.database import get_db
from app.repositories.asset_repository import AssetRepository
from app.repositories.news_article_repository import NewsArticleRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.services.news.providers.base import NewsProvider
from app.services.news.providers.exceptions import NewsProviderConfigurationError
from app.services.news.providers.mock import MockNewsProvider
from app.services.news.providers.newsapi import NewsApiProvider
from app.services.news_ingestion_pipeline import NewsIngestionPipeline
from app.services.news_sentiment.ai_summary_generator import AISummaryGenerator
from app.services.news_sentiment_engine import NewsSentimentEngine


def _build_newsapi_provider() -> NewsProvider:
    if not settings.news_api_key:
        raise NewsProviderConfigurationError(
            "newsapi is configured in news_providers but NEWS_API_KEY is not set"
        )
    return NewsApiProvider(
        api_key=settings.news_api_key,
        base_url=settings.news_api_base_url,
        timeout=settings.news_api_timeout_seconds,
    )


_PROVIDER_FACTORIES: dict[str, Callable[[], NewsProvider]] = {
    "mock": MockNewsProvider,
    "newsapi": _build_newsapi_provider,
}


def get_news_providers() -> list[NewsProvider]:
    """Build the configured news provider chain (docs/46 §8, ADR-050).

    Mirrors `app.dependencies.market_data.get_market_data_providers` -
    this is the only place that knows concrete provider classes exist.
    No `RateLimitedProvider` wrapping for `newsapi` yet (docs/46 §13's
    explicit decision to skip rate limiting until a real, paid vendor is
    integrated) - NewsAPI.org's free tier has no per-minute burst limit
    that this ingestion cadence (`news_ingestion_interval_seconds`) would
    threaten.
    """
    providers: list[NewsProvider] = []
    for name in settings.news_providers:
        factory = _PROVIDER_FACTORIES.get(name)
        if factory is None:
            raise NewsProviderConfigurationError(f"Unknown news provider configured: {name!r}")
        providers.append(factory())
    return providers


def get_news_source_repository(db: Annotated[Session, Depends(get_db)]) -> NewsSourceRepository:
    return NewsSourceRepository(db)


def get_news_article_repository(db: Annotated[Session, Depends(get_db)]) -> NewsArticleRepository:
    return NewsArticleRepository(db)


def get_news_sentiment_repository(
    db: Annotated[Session, Depends(get_db)],
) -> NewsSentimentRepository:
    return NewsSentimentRepository(db)


def get_news_sentiment_engine(
    sentiment_repository: Annotated[
        NewsSentimentRepository, Depends(get_news_sentiment_repository)
    ],
) -> NewsSentimentEngine:
    return NewsSentimentEngine(sentiment_repository=sentiment_repository)


def get_news_ingestion_pipeline(
    db: Annotated[Session, Depends(get_db)],
) -> NewsIngestionPipeline:
    return NewsIngestionPipeline(
        providers=get_news_providers(),
        source_repository=NewsSourceRepository(db),
        article_repository=NewsArticleRepository(db),
        sentiment_repository=NewsSentimentRepository(db),
        asset_repository=AssetRepository(db),
        ai_summary_generator=AISummaryGenerator(),
    )

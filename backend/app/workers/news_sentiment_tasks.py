from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.news import get_news_providers
from app.repositories.asset_repository import AssetRepository
from app.repositories.news_article_repository import NewsArticleRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.services.ingestion_health import record_failure, record_success
from app.services.news.providers.exceptions import AllNewsProvidersFailedError
from app.services.news_ingestion_pipeline import NewsIngestionPipeline, default_since
from app.services.news_sentiment.ai_summary_generator import AISummaryGenerator
from app.workers.celery_app import celery_app


@celery_app.task(name="news_sentiment.ingest")  # type: ignore[untyped-decorator]
def ingest_news_task() -> int:
    """Single scheduled ingestion task (docs/46 §3/§12), mirroring
    `market_data_tasks.collect_market_data_task`'s shape. Idempotent:
    `dedup_detector` skips articles already ingested in the lookback
    window, so re-running an overlapping window is safe.

    Phase 9G (ADR-139): re-raises `AllNewsProvidersFailedError` after
    recording the failure - Celery must report this run as FAILED, not
    a clean success with a zero count, when every configured provider
    failed.
    """
    session = SessionLocal()
    try:
        pipeline = NewsIngestionPipeline(
            providers=get_news_providers(),
            source_repository=NewsSourceRepository(session),
            article_repository=NewsArticleRepository(session),
            sentiment_repository=NewsSentimentRepository(session),
            asset_repository=AssetRepository(session),
            ai_summary_generator=AISummaryGenerator(),
        )
        since = default_since(settings.news_lookback_hours)
        try:
            result = pipeline.run(since)
        except AllNewsProvidersFailedError as exc:
            record_failure("news", str(exc))
            raise
        record_success("news")
        return result.ingested
    finally:
        session.close()


def register_news_schedule() -> dict[str, dict[str, object]]:
    """Build the Celery Beat schedule entry for news ingestion (docs/46
    §12). Unlike market data's per-timeframe schedule, there is exactly
    one entry - News has no timeframe concept (docs/46 §10)."""
    return {
        "ingest-news": {
            "task": "news_sentiment.ingest",
            "schedule": float(settings.news_ingestion_interval_seconds),
        }
    }

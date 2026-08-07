from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.economic_calendar import get_economic_calendar_providers
from app.repositories.economic_event_repository import EconomicEventRepository
from app.services.economic_calendar.providers.exceptions import (
    AllEconomicCalendarProvidersFailedError,
)
from app.services.economic_calendar_ingestion_pipeline import (
    EconomicCalendarIngestionPipeline,
    default_window,
)
from app.services.ingestion_health import record_failure, record_success
from app.workers.celery_app import celery_app


@celery_app.task(name="economic_calendar.ingest")  # type: ignore[untyped-decorator]
def ingest_economic_calendar_task() -> tuple[int, int]:
    """Single scheduled ingestion task (docs/47 §3/§6), mirroring
    `news_sentiment_tasks.ingest_news_task`'s shape. Idempotent via
    upsert-by-natural-key (ADR-058), not skip-on-duplicate - re-running
    an overlapping window is safe and is how revisions/newly-released
    actual values are captured.

    Phase 9G (ADR-139): re-raises `AllEconomicCalendarProvidersFailedError`
    after recording the failure - Celery must report this run as
    FAILED, not a clean success, when every configured provider failed.
    """
    session = SessionLocal()
    try:
        pipeline = EconomicCalendarIngestionPipeline(
            providers=get_economic_calendar_providers(),
            event_repository=EconomicEventRepository(session),
        )
        start, end = default_window(
            settings.economic_calendar_lookback_days, settings.economic_calendar_lookahead_days
        )
        try:
            result = pipeline.run(start, end)
        except AllEconomicCalendarProvidersFailedError as exc:
            record_failure("economic_calendar", str(exc))
            raise
        record_success("economic_calendar")
        return result.created, result.updated
    finally:
        session.close()


def register_economic_calendar_schedule() -> dict[str, dict[str, object]]:
    """Build the Celery Beat schedule entry for economic calendar
    ingestion (docs/47 §6). Exactly one entry, mirroring News - Economic
    Calendar has no timeframe concept either (docs/47 §9)."""
    return {
        "ingest-economic-calendar": {
            "task": "economic_calendar.ingest",
            "schedule": float(settings.economic_calendar_ingestion_interval_seconds),
        }
    }

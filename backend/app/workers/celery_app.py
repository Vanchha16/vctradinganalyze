from celery import Celery
from celery.signals import setup_logging, worker_ready

from app.config import settings
from app.core.logging import configure_logging

celery_app = Celery("claudetrading", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, timezone="UTC")


@setup_logging.connect  # type: ignore[untyped-decorator]  # celery ships no decorator stubs
def _configure_worker_logging(*_: object, **__: object) -> None:
    """Replace Celery's default logging setup with the shared structlog config."""
    configure_logging(settings.log_level)


@worker_ready.connect  # type: ignore[untyped-decorator]  # celery ships no decorator stubs
def _log_active_ingestion_providers(*_: object, **__: object) -> None:
    """Phase 9G (ADR-139) - mock provider usage must never be silently
    discovered later; log it once when the worker (where ingestion
    actually runs) finishes booting."""
    from app.services.ingestion_health import log_active_providers

    log_active_providers()


@worker_ready.connect  # type: ignore[untyped-decorator]  # celery ships no decorator stubs
def _log_market_data_quota_projection(*_: object, **__: object) -> None:
    """Phase 9H (ADR-140) - a schedule that cannot fit its provider's
    documented daily cap has now caused a silent outage twice (here and in
    news ingestion, `5ca5985`); log the projected daily request count once
    at worker startup so this class of mistake is visible immediately
    rather than discovered hours into a production outage."""
    from app.workers.market_data_tasks import log_quota_projection

    log_quota_projection()


# Imported after `celery_app` is defined above (the task modules import it
# back) - registers each domain's task(s) and Beat schedule.
from app.workers import (  # noqa: E402
    economic_calendar_tasks,
    market_data_tasks,
    news_sentiment_tasks,
    signal_monitoring_tasks,
    signal_tasks,
    telegram_tasks,
)

celery_app.conf.beat_schedule = {
    **market_data_tasks.register_market_data_schedule(),
    **news_sentiment_tasks.register_news_schedule(),
    **economic_calendar_tasks.register_economic_calendar_schedule(),
    **signal_tasks.register_signal_schedule(),
    **signal_monitoring_tasks.register_signal_monitoring_schedule(),
    **telegram_tasks.register_telegram_schedule(),
}

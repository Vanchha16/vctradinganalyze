from celery import Celery
from celery.signals import setup_logging

from app.config import settings
from app.core.logging import configure_logging

celery_app = Celery("claudetrading", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, timezone="UTC")


@setup_logging.connect  # type: ignore[untyped-decorator]  # celery ships no decorator stubs
def _configure_worker_logging(*_: object, **__: object) -> None:
    """Replace Celery's default logging setup with the shared structlog config."""
    configure_logging(settings.log_level)


# Imported after `celery_app` is defined above (the task modules import it
# back) - registers each domain's task(s) and Beat schedule.
from app.workers import (  # noqa: E402
    economic_calendar_tasks,
    market_data_tasks,
    news_sentiment_tasks,
)

celery_app.conf.beat_schedule = {
    **market_data_tasks.register_market_data_schedule(),
    **news_sentiment_tasks.register_news_schedule(),
    **economic_calendar_tasks.register_economic_calendar_schedule(),
}

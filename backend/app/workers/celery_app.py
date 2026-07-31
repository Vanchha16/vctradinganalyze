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


# Imported after `celery_app` is defined above (the task module imports it
# back) - registers the market-data collection task and its Beat schedule.
from app.workers import market_data_tasks  # noqa: E402

celery_app.conf.beat_schedule = market_data_tasks.register_market_data_schedule()

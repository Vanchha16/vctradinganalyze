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

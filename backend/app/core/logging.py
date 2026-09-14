import logging

import structlog
from structlog.types import EventDict, WrappedLogger

_SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "api_key"}

#: HTTP client libraries that log full request URLs at INFO.
_URL_LOGGING_LIBRARIES = ("httpx", "httpcore")


def _redact_sensitive_keys(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    for key in list(event_dict):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging(log_level: str) -> None:
    """Configure structured JSON logging shared by FastAPI and Celery workers.

    Safe to call from either the FastAPI lifespan or a Celery worker's
    `setup_logging` signal handler - it only touches the stdlib root logger,
    which both processes use as their logging backbone.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _redact_sensitive_keys,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.propagate = False

    # httpx logs every request URL at INFO, and the Telegram Bot API puts the
    # bot token in the URL path - so each poll wrote the token to the worker
    # log (found 2026-09-14). Warnings and errors still come through.
    for logger_name in _URL_LOGGING_LIBRARIES:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

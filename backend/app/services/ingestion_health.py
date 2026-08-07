"""Ingestion health tracking (Phase 9G, ADR-139).

Production had zero news articles while the economic calendar silently
served mock data - both pipelines reported success, because a provider
failure only ever logged a warning and returned an empty result,
indistinguishable from "nothing to ingest today." This module gives
`NewsIngestionPipeline`/`EconomicCalendarIngestionPipeline` a shared
per-provider outcome shape (§3's case 1/2/3 distinction), and stores
each pipeline's last-run outcome in Redis - already a dependency, same
pattern `app/dependencies/rate_limit.py`/`quota.py` already use for
small counters - rather than adding a migration for an ingestion-run
table that nothing else needs.

Read by `AdminSystemService.get_system_status` (`GET /admin/system`);
written by both the scheduled Celery task and the admin-triggered
refresh action for each pipeline, so either path updates the same
health record. Fail-open on both read and write - a Redis outage must
never break an ingestion run or take down `GET /admin/system` (the same
rule ADR-130 already set for that endpoint's DB/Redis liveness checks).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

import redis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# Module-level client, created once - mirrors `app/dependencies/quota.py`'s
# `_redis_client` (not per-call), since ingestion runs happen far more
# often than a Redis connection should be re-established.
_redis_client: redis.Redis = redis.Redis.from_url(settings.redis_url)

Pipeline = Literal["news", "economic_calendar"]


@dataclass(frozen=True, slots=True)
class ProviderOutcome:
    """One provider's result for a single ingestion run - the unit both
    pipelines' results are built from, and what a case-3 "provider
    failed" entry looks like versus a case-1/2 success (count may be 0)."""

    provider: str
    success: bool
    count: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class IngestionHealthStatus:
    providers: list[str]
    uses_mock: bool
    last_success_at: datetime | None
    last_error: str | None


def _key(pipeline: Pipeline, field: str) -> str:
    return f"ingestion_health:{pipeline}:{field}"


def record_success(pipeline: Pipeline) -> None:
    try:
        _redis_client.set(_key(pipeline, "last_success_at"), datetime.now(UTC).isoformat())
        _redis_client.delete(_key(pipeline, "last_error"))
    except Exception:  # noqa: BLE001 - fail open, same rule quota/rate_limit follow
        logger.warning("ingestion_health.record_success_failed", pipeline=pipeline, exc_info=True)


def record_failure(pipeline: Pipeline, error: str) -> None:
    try:
        _redis_client.set(_key(pipeline, "last_error"), error)
    except Exception:  # noqa: BLE001 - fail open, same rule quota/rate_limit follow
        logger.warning("ingestion_health.record_failure_failed", pipeline=pipeline, exc_info=True)


def get_health(
    pipeline: Pipeline, *, providers: list[str], uses_mock: bool
) -> IngestionHealthStatus:
    """Fail-open read - if Redis itself is unreachable, returns a status
    with `None` timestamps/error rather than raising, so `GET
    /admin/system` still returns 200 (ADR-130's established rule, tested
    explicitly per the build spec §8)."""
    try:
        # `.get()` is typed `Awaitable[Any] | Any` to also cover redis-py's
        # async client - both current callers only ever use the
        # synchronous `redis.Redis`, which genuinely returns `bytes |
        # None` here. Same documented gap `redis_fixed_window.py` casts
        # around for `.incr()`.
        raw_success_at = cast(
            "bytes | None", _redis_client.get(_key(pipeline, "last_success_at"))
        )
        raw_error = cast("bytes | None", _redis_client.get(_key(pipeline, "last_error")))
    except Exception:  # noqa: BLE001 - fail open, same rule quota/rate_limit follow
        logger.warning("ingestion_health.read_failed", pipeline=pipeline, exc_info=True)
        return IngestionHealthStatus(
            providers=providers, uses_mock=uses_mock, last_success_at=None, last_error=None
        )

    last_success_at = (
        datetime.fromisoformat(raw_success_at.decode()) if raw_success_at is not None else None
    )
    last_error = raw_error.decode() if raw_error is not None else None
    return IngestionHealthStatus(
        providers=providers,
        uses_mock=uses_mock,
        last_success_at=last_success_at,
        last_error=last_error,
    )


def log_active_providers() -> None:
    """Item C (ADR-139): mock usage must be explicit, never a silent
    fallback discovered later. Logs which provider(s) are configured for
    News and Economic Calendar, and whether either is a mock, once at
    process startup (both the FastAPI app and the Celery worker call
    this - ingestion actually runs in the worker, but the API process
    logging it too means an operator inspecting either log stream sees
    the same answer). Deferred imports avoid a circular import (`app.
    dependencies.news`/`economic_calendar` import the pipeline classes,
    which import this module for `ProviderOutcome`)."""
    from app.dependencies.economic_calendar import get_economic_calendar_providers
    from app.dependencies.news import get_news_providers

    news_providers = get_news_providers()
    calendar_providers = get_economic_calendar_providers()

    logger.info(
        "ingestion.providers_configured",
        pipeline="news",
        providers=[p.name for p in news_providers],
        uses_mock=any(p.name == "mock" for p in news_providers),
    )
    logger.info(
        "ingestion.providers_configured",
        pipeline="economic_calendar",
        providers=[p.name for p in calendar_providers],
        uses_mock=any(p.name == "mock" for p in calendar_providers),
    )


__all__ = [
    "IngestionHealthStatus",
    "ProviderOutcome",
    "get_health",
    "log_active_providers",
    "record_failure",
    "record_success",
]

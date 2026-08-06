"""Per-IP rate limiting for the public (unauthenticated) analysis/data
routes (Phase 9A, ADR-132, docs/60 §4.2).

Extends `app/dependencies/quota.py`'s Redis fixed-window pattern rather
than adding a library (`slowapi` or otherwise) - Redis and a working
fixed-window implementation already exist here. The differences from
ADR-127's per-user quota: keyed by client IP (via `app.core.client_ip`,
never a naively-trusted `X-Forwarded-For`) instead of user id, and applied
at the router level in `app/api/v1/router.py` (`include_router(...,
dependencies=[...])`) rather than decorating each handler individually,
since there are ~30 public handlers across nine modules and decorating
them one by one invites omissions.

Fail-open by design, same rationale as `quota.py`: a Redis outage must
never take the public site down - the goal of this limiter is stopping
abuse, not being a hard security boundary.
"""

import logging
from collections.abc import Callable

import redis
from fastapi import Request

from app.config import settings
from app.core.client_ip import get_client_ip
from app.exceptions import QuotaExceededException

logger = logging.getLogger(__name__)

# Separate module-level client from `quota.py`'s, mirroring the existing
# precedent of multiple independent `redis.Redis.from_url` instances in
# this codebase (see `quota.py`'s own comment about `routes/health.py`) -
# not worth merging for a connection pool that costs nothing idle.
_redis_client: redis.Redis = redis.Redis.from_url(settings.redis_url)


def rate_limit_public(bucket: str, limit: int, window_seconds: int) -> Callable[[Request], None]:
    """Build a dependency enforcing a per-IP fixed-window rate limit.

    Usage: `Depends(rate_limit_public("public_engine",
    settings.public_rate_limit_engine_limit,
    settings.public_rate_limit_window_seconds))`, attached via
    `include_router(..., dependencies=[...])` so it runs for every route
    on that router without touching individual handlers.
    """

    def _check_rate_limit(request: Request) -> None:
        ip = get_client_ip(request) or "unknown"
        key = f"ratelimit:{bucket}:{ip}"

        try:
            count = _redis_client.incr(key)
            if count == 1:
                _redis_client.expire(key, window_seconds)
        except Exception as exc:  # noqa: BLE001 - fail open on any Redis failure
            logger.warning(
                "Rate limit check failed for bucket=%s ip=%s, failing open: %s",
                bucket,
                ip,
                exc,
            )
            return

        if count > limit:
            raise QuotaExceededException(
                f"Rate limit exceeded for {bucket}: {limit} requests per "
                f"{window_seconds} seconds. Please try again later."
            )

    return _check_rate_limit

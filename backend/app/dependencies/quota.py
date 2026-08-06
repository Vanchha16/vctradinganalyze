"""Per-user request quota for the two LLM-token-spending endpoints
(ADR-127, docs/36). `get_current_user` (Phase 2C) remains authentication-
only by design. This module is purely additive on top of it: it composes
`get_current_user` via `Depends()`, the same pattern `app/dependencies/
rbac.py` (Phase 8B) already established for role checks, and does not
modify it.

This is deliberately NOT a general-purpose API rate limiter - it is a
narrow cost guard for `POST /analysis/ai/{symbol}` and `POST
/chat/conversations/{id}/messages`, the only two routes that spend real
OpenAI tokens per call. General inbound API rate limiting remains an open
question tracked in BACKLOG.md §3.

Fail-open by design: if Redis is unreachable or raises any exception, the
request is allowed through and a warning is logged. A cache outage must
never take down a core product feature over a soft cost guard - the same
degrade-rather-than-block philosophy `app/services/news_sentiment/
ai_summary_generator.py` uses for its own OpenAI call (ADR-051).
"""

import logging
from collections.abc import Callable
from typing import Annotated

import redis
from fastapi import Depends

from app.config import settings
from app.dependencies.auth import get_current_user
from app.exceptions import QuotaExceededException
from app.models.user import User

logger = logging.getLogger(__name__)

# Module-level client/connection pool, created once - not per-request.
# Mirrors the `redis.Redis.from_url` call in `app/api/v1/routes/health.py`,
# but that route creates a fresh client per healthcheck request, which is
# fine for an occasional readiness probe and not appropriate on a hot path
# like these two AI endpoints.
_redis_client: redis.Redis = redis.Redis.from_url(settings.redis_url)


def require_quota(bucket: str, limit: int, window_seconds: int) -> Callable[..., User]:
    """Build a dependency enforcing a per-user fixed-window quota.

    Usage: `Depends(require_quota("ai_analysis", settings.ai_analysis_quota_limit,
    settings.ai_analysis_quota_window_seconds))`.

    The Redis key includes both `bucket` and the user id so different
    buckets (AI analysis vs. chat) never share a budget, and different
    users never share each other's budget. No role is exempt from this
    check, including Super Admin - an explicit product decision (ADR-127).
    """

    def _check_quota(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        key = f"quota:{bucket}:{current_user.id}"

        try:
            count = _redis_client.incr(key)
            if count == 1:
                _redis_client.expire(key, window_seconds)
        except Exception as exc:  # noqa: BLE001 - fail open on any Redis failure
            logger.warning(
                "Quota check failed for bucket=%s user=%s, failing open: %s",
                bucket,
                current_user.id,
                exc,
            )
            return current_user

        if count > limit:
            raise QuotaExceededException(
                f"You have exceeded the {bucket} quota of {limit} requests "
                f"per {window_seconds} seconds. Please try again later."
            )

        return current_user

    return _check_quota

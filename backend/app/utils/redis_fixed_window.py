"""Shared fixed-window Redis counter check (cleanup spec, 2026-08-06),
used by both `app/dependencies/rate_limit.py` (per-IP) and
`app/dependencies/quota.py` (per-user) - the two modules' `incr`/`expire`/
compare logic was byte-for-byte identical, only the Redis key and each
caller's error-handling/logging/fallback differed. Centralizing removes
that duplication and gives redis-py's typing gap exactly one place to be
resolved instead of two: `incr` is typed `ResponseT`, a union that also
covers the async client, even though both callers only ever use the
synchronous `redis.Redis` - which genuinely returns `int` here, hence the
`cast` below.
"""

from typing import cast

import redis


def increment_and_check(
    redis_client: redis.Redis, key: str, limit: int, window_seconds: int
) -> bool:
    """Increment `key`'s fixed-window counter, set its expiry on the first
    increment, and return whether it has now exceeded `limit`.

    Raises whatever `incr`/`expire` raises on a Redis failure - both
    current callers wrap this in their own fail-open `try/except`, since
    they log differently (bucket+IP vs. bucket+user id) and fall back to
    different return values.
    """
    count = cast(int, redis_client.incr(key))
    if count == 1:
        redis_client.expire(key, window_seconds)
    return count > limit

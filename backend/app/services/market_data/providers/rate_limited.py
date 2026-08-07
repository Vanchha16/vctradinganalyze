import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import redis
import structlog

from app.config import settings
from app.models.enums import Timeframe
from app.services.market_data.exceptions import DailyQuotaExceededError
from app.services.market_data.providers.base import (
    MarketDataProvider,
    ProviderCapabilities,
    RawCandle,
)
from app.utils.redis_fixed_window import increment_and_check

logger = structlog.get_logger(__name__)

# Module-level client, created once - mirrors `app/dependencies/quota.py`'s
# `_redis_client` (not per-call/per-instance). Cleanup (2026-08-07): the
# daily counter used to live on `self._daily_used`, an in-memory instance
# attribute - but `get_market_data_providers()` builds a brand-new
# `RateLimitedProvider` on every single Celery task invocation
# (`market_data_tasks.py`), so that counter reset to 0 every run and could
# never reach its own configured cap before being thrown away. Real usage
# kept accumulating against Twelve Data's own server-side counter, unseen,
# until Twelve Data itself cut the key off - the exact incident this fixes.
# Redis (already required) is the shared store that survives both task
# boundaries and worker restarts, same pattern this project's other
# cross-request counters (`rate_limit.py`/`quota.py`) already use.
_redis_client: redis.Redis = redis.Redis.from_url(settings.redis_url)

#: Safety-net cleanup only - the actual daily reset is the UTC-date-keyed
#: Redis key changing at midnight, not this TTL. A couple of days' margin
#: means a late-arriving request for "yesterday" (Celery clock skew, a
#: delayed retry) still lands on the correct existing key instead of
#: silently starting a fresh counter for an already-expired day.
_QUOTA_KEY_TTL_SECONDS = 2 * 24 * 60 * 60


class RateLimitedProvider:
    """Wraps any `MarketDataProvider`, enforcing a requests-per-minute cap
    (token bucket, in-memory) and, optionally, a requests-per-day cap
    (Redis-backed, ADR-025) - a decorator around the provider, not logic
    inside `MarketDataService` (docs/40), so the orchestration layer stays
    provider-agnostic and every provider gets consistent throttling for
    free just by being wrapped.

    The per-minute cap blocks (sleeps) rather than raising, since it is an
    expected, self-resolving condition within seconds. The daily cap
    instead *raises* `DailyQuotaExceededError` once exhausted - sleeping
    until the next UTC day would stall a Celery task for hours, which
    `MarketDataService`'s existing retry/failover handles far better than
    blocking would.

    **Known, accepted limitation (2026-08-07):** the per-minute token
    bucket is still in-memory, still reset on every fresh instance (i.e.
    every task run) - unlike the daily cap, it was not moved to Redis.
    It still does real work smoothing a burst of calls *within* one task
    run (e.g. looping over several assets), which is a genuine partial
    benefit; it just does not coordinate across separate task
    invocations or worker processes. A Redis-backed token bucket needs an
    atomic read-refill-decrement (a Lua script, not a plain `INCR`) -
    a real design task of its own, not folded into this fix.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        requests_per_minute: float,
        *,
        requests_per_day: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._provider = provider
        self.name = provider.name

        self._rate_per_second = requests_per_minute / 60
        self._capacity = requests_per_minute
        self._tokens = requests_per_minute
        self._clock = clock
        self._sleep = sleep
        self._last_refill = clock()

        self._requests_per_day = requests_per_day
        self._now = now

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        self._check_daily_quota()
        self._acquire_minute_token()
        return self._provider.get_candles(symbol, timeframe, start, end)

    def health_check(self) -> bool:
        return self._provider.health_check()

    def capabilities(self) -> ProviderCapabilities:
        return self._provider.capabilities()

    def _daily_quota_key(self, day: datetime) -> str:
        return f"market_data_quota:{self.name}:{day.strftime('%Y-%m-%d')}"

    def _check_daily_quota(self) -> None:
        if self._requests_per_day is None:
            return

        now = self._now()
        key = self._daily_quota_key(now)
        try:
            exceeded = increment_and_check(
                _redis_client, key, int(self._requests_per_day), _QUOTA_KEY_TTL_SECONDS
            )
        except Exception:  # noqa: BLE001 - fail open, same rule quota/rate_limit follow
            logger.warning("market_data_quota.check_failed", provider=self.name, exc_info=True)
            return

        if exceeded:
            day_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
            raise DailyQuotaExceededError(
                provider=self.name,
                used=self._requests_per_day,
                limit=self._requests_per_day,
                reset_at=day_start + timedelta(days=1),
            )

    def _acquire_minute_token(self) -> None:
        while True:
            now = self._clock()
            self._tokens = min(
                self._capacity, self._tokens + (now - self._last_refill) * self._rate_per_second
            )
            self._last_refill = now

            if self._tokens >= 1:
                self._tokens -= 1
                return

            self._sleep((1 - self._tokens) / self._rate_per_second)

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.models.enums import Timeframe
from app.services.market_data.exceptions import DailyQuotaExceededError
from app.services.market_data.providers.base import (
    MarketDataProvider,
    ProviderCapabilities,
    RawCandle,
)


class RateLimitedProvider:
    """Wraps any `MarketDataProvider`, enforcing a requests-per-minute cap
    (token bucket) and, optionally, a requests-per-day cap - a decorator
    around the provider, not logic inside `MarketDataService` (docs/40), so
    the orchestration layer stays provider-agnostic and every provider gets
    consistent throttling for free just by being wrapped.

    The per-minute cap blocks (sleeps) rather than raising, since it is an
    expected, self-resolving condition within seconds. The daily cap
    (ADR-025) instead *raises* `DailyQuotaExceededError` once exhausted -
    sleeping until the next UTC day would stall a Celery task for hours,
    which `MarketDataService`'s existing retry/failover handles far better
    than blocking would.
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
        self._day_start = self._utc_day_start()
        self._daily_used = 0.0

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        self._check_daily_quota()
        self._acquire_minute_token()
        self._daily_used += 1
        return self._provider.get_candles(symbol, timeframe, start, end)

    def health_check(self) -> bool:
        return self._provider.health_check()

    def capabilities(self) -> ProviderCapabilities:
        return self._provider.capabilities()

    def _utc_day_start(self) -> datetime:
        current = self._now()
        return datetime(current.year, current.month, current.day, tzinfo=UTC)

    def _check_daily_quota(self) -> None:
        if self._requests_per_day is None:
            return

        day_start = self._utc_day_start()
        if day_start != self._day_start:
            self._day_start = day_start
            self._daily_used = 0.0

        if self._daily_used >= self._requests_per_day:
            raise DailyQuotaExceededError(
                provider=self.name,
                used=self._daily_used,
                limit=self._requests_per_day,
                reset_at=self._day_start + timedelta(days=1),
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

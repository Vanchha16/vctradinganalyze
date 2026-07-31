import time
from collections.abc import Callable
from datetime import datetime

from app.models.enums import Timeframe
from app.services.market_data.providers.base import (
    MarketDataProvider,
    ProviderCapabilities,
    RawCandle,
)


class RateLimitedProvider:
    """Wraps any `MarketDataProvider`, enforcing a requests-per-minute cap
    via a token bucket - a decorator around the provider, not logic inside
    `MarketDataService` (docs/40), so the orchestration layer stays
    provider-agnostic and every provider gets consistent throttling for
    free just by being wrapped.

    Blocks (sleeps) rather than raising when the bucket is empty, since a
    rate limit is an expected, self-resolving condition - not a failure
    `MarketDataService`'s retry/failover logic needs to know about.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        requests_per_minute: float,
        *,
        clock: Callable[[], float] = time.monotonic,
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

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        self._acquire_token()
        return self._provider.get_candles(symbol, timeframe, start, end)

    def health_check(self) -> bool:
        return self._provider.health_check()

    def capabilities(self) -> ProviderCapabilities:
        return self._provider.capabilities()

    def _acquire_token(self) -> None:
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

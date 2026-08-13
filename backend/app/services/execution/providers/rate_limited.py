import time
from collections.abc import Callable

from app.models.enums import SignalType
from app.services.execution.providers.base import (
    AccountSnapshot,
    OpenPosition,
    OrderExecutionProvider,
    OrderPlacementResult,
    SymbolSpecification,
)


class RateLimitedExecutionProvider:
    """Wraps any `OrderExecutionProvider`, enforcing a requests-per-minute
    cap (in-memory token bucket) - mirrors
    `app.services.market_data.providers.rate_limited.RateLimitedProvider`'s
    shape/tradeoffs (same in-memory-only limitation: resets per process,
    does not coordinate across Celery workers). No daily-quota tier here
    (unlike market data's Redis-backed ADR-025 cap) - this system places
    at most a handful of real orders per day by design (§3D's max-1-
    concurrent-position rule), nowhere near needing a daily ceiling; the
    per-minute cap alone exists to keep a buggy retry loop from hammering
    a real-money account's bridge connection.
    """

    def __init__(
        self,
        provider: OrderExecutionProvider,
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

    def get_account_snapshot(self) -> AccountSnapshot:
        self._acquire_token()
        return self._provider.get_account_snapshot()

    def get_symbol_specification(self, symbol: str) -> SymbolSpecification:
        self._acquire_token()
        return self._provider.get_symbol_specification(symbol)

    def get_open_positions(self, symbol: str) -> list[OpenPosition]:
        self._acquire_token()
        return self._provider.get_open_positions(symbol)

    def place_limit_order(
        self,
        *,
        symbol: str,
        direction: SignalType,
        volume: float,
        open_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> OrderPlacementResult:
        self._acquire_token()
        return self._provider.place_limit_order(
            symbol=symbol,
            direction=direction,
            volume=volume,
            open_price=open_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    def health_check(self) -> bool:
        return self._provider.health_check()

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


__all__ = ["RateLimitedExecutionProvider"]

import hashlib
import random
from datetime import datetime

from app.models.enums import Timeframe
from app.services.market_data.providers.base import RawCandle
from app.services.market_data.timeframe_utils import TIMEFRAME_DURATIONS

_BASE_PRICES: dict[str, float] = {
    "XAUUSD": 2400.0,
    "BTCUSD": 65000.0,
}
_DEFAULT_BASE_PRICE = 1.1000


def _seed_for(symbol: str, timeframe: Timeframe) -> int:
    """A stable seed derived from symbol+timeframe, independent of Python's
    per-process hash randomization - so generated candles are reproducible
    across test runs and processes."""
    digest = hashlib.sha256(f"{symbol}:{timeframe.value}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


class MockMarketDataProvider:
    """Synthetic OHLCV generator for Phase 3A (docs/38). Never fails, never
    calls an external service - Phase 3B adds the first real provider."""

    name = "mock"

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        step = TIMEFRAME_DURATIONS[timeframe]
        rng = random.Random(_seed_for(symbol, timeframe))
        price = _BASE_PRICES.get(symbol, _DEFAULT_BASE_PRICE)

        candles: list[RawCandle] = []
        timestamp = start
        while timestamp <= end:
            open_price = price
            close_price = max(0.0001, open_price + rng.uniform(-1, 1) * open_price * 0.001)
            high_price = max(open_price, close_price) + abs(rng.uniform(0, 1)) * open_price * 0.0005
            low_price = min(open_price, close_price) - abs(rng.uniform(0, 1)) * open_price * 0.0005
            volume = abs(rng.uniform(100, 10_000))

            candles.append(
                RawCandle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
            )
            price = close_price
            timestamp = timestamp + step

        return candles

    def health_check(self) -> bool:
        return True

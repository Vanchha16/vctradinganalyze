from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.enums import Timeframe


@dataclass(frozen=True, slots=True)
class RawCandle:
    """OHLCV data as returned by a provider, before normalization/validation.

    Values are left as the provider returned them (typically `float`) -
    `app.services.market_data.normalization.normalize_candle` converts
    these to the `Decimal`/UTC-aware shape used for persistence.
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class MarketDataProvider(Protocol):
    """Interface every market-data provider implements (docs/38 §2).

    `MarketDataService` depends only on this interface, never on a
    concrete provider class (docs/06 §5) - which provider(s) it receives
    is a wiring concern (`app/dependencies/market_data.py`).
    """

    name: str

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        """Fetch OHLCV candles for a canonical symbol/timeframe over a UTC range.

        Raises `TransientProviderError` for retryable failures,
        `PermanentProviderError` (or `UnsupportedTimeframeError`) for
        failures that should move on to the next provider without retrying.
        """
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not fetch real data."""
        ...

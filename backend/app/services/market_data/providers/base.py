from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.models.enums import MarketType, Timeframe


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


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """What a provider can be asked to do (docs/40).

    A structured value object rather than a single `supports(...)` method,
    so new capability dimensions (e.g. a future `max_symbols_per_request`)
    can be added as new fields - with defaults, so existing providers keep
    working unchanged - instead of requiring a breaking signature change
    every time a new dimension is needed.

    `supported_market_types` is required, not optional-defaulting-to-"no
    restriction" - every provider must say explicitly which market types
    it covers (e.g. `frozenset(MarketType)` if it genuinely covers all of
    them), rather than relying on `None` as an ambiguous "supports
    everything" sentinel that's easy to set by accident.
    """

    supported_timeframes: frozenset[Timeframe]
    supported_market_types: frozenset[MarketType]
    max_lookback: timedelta | None = None  # None = no known limit (distinct concept - see below)

    def supports(self, timeframe: Timeframe, *, market_type: MarketType | None = None) -> bool:
        if timeframe not in self.supported_timeframes:
            return False
        if market_type is not None and market_type not in self.supported_market_types:
            return False
        return True


class MarketDataProvider(Protocol):
    """Interface every market-data provider implements (docs/38 §2, docs/40).

    `MarketDataService` depends only on this interface, never on a
    concrete provider class (docs/06 §5) - which provider(s) it receives,
    and any rate limiting applied to them, is a wiring concern
    (`app/dependencies/market_data.py`), not something implementations or
    callers need to know about.
    """

    name: str

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        """Fetch OHLCV candles for a canonical symbol/timeframe over a UTC range.

        Raises `TransientProviderError` for retryable failures,
        `PermanentProviderError` (or a more specific subclass) for
        failures that should move on to the next provider without retrying.
        """
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not fetch real data."""
        ...

    def capabilities(self) -> ProviderCapabilities:
        """Declare what this provider supports, so `MarketDataService` can
        skip a call it already knows will fail (docs/40) rather than
        discover it reactively and waste a request against a rate-limited
        API."""
        ...


__all__ = ["MarketDataProvider", "ProviderCapabilities", "RawCandle"]

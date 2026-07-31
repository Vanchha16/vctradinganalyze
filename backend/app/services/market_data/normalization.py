from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import Timeframe
from app.services.market_data.providers.base import RawCandle


@dataclass(frozen=True, slots=True)
class NormalizedCandle:
    """A candle after normalization, before validation.

    Prices are `Decimal` (not `float`) to avoid floating-point drift in
    stored price data, and the timestamp is UTC-aware.
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None


def normalize_candle(raw: RawCandle) -> NormalizedCandle:
    """Convert provider-native OHLCV values to the shape used for validation
    and persistence. Naive timestamps are assumed to already be UTC (no
    provider integrated so far documents a different source timezone -
    docs/38 §5)."""
    timestamp = (
        raw.timestamp if raw.timestamp.tzinfo is not None else raw.timestamp.replace(tzinfo=UTC)
    )
    timestamp = timestamp.astimezone(UTC)

    return NormalizedCandle(
        symbol=raw.symbol,
        timeframe=raw.timeframe,
        timestamp=timestamp,
        open=Decimal(str(raw.open)),
        high=Decimal(str(raw.high)),
        low=Decimal(str(raw.low)),
        close=Decimal(str(raw.close)),
        volume=Decimal(str(raw.volume)) if raw.volume is not None else None,
    )

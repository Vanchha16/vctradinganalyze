"""Shared candle-construction helpers for SMC analyzer tests - builds
synthetic OHLCV fixtures engineered to contain known patterns, not
randomized data."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.price_candle import PriceCandle

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_candle(
    index: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    *,
    volume: float | None = 1000.0,
) -> PriceCandle:
    return PriceCandle(
        timestamp=_BASE + timedelta(hours=index),
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(volume)) if volume is not None else None,
    )


def make_candles(specs: list[tuple[float, float, float, float]]) -> list[PriceCandle]:
    """`specs` is a list of (open, high, low, close) tuples, oldest-first."""
    return [make_candle(i, *spec) for i, spec in enumerate(specs)]

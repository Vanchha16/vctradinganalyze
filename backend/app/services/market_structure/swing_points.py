"""Shared swing-high/low detection (classic fractal method), used by both
the Technical Analysis Engine (docs/42 §6, `SupportResistanceAnalyzer`)
and the SMC Engine (docs/43, `MarketStructureAnalyzer`) - extracted here
so neither duplicates the other's logic. Both docs/08 §3 and docs/09 §3
list swing highs/lows as required input.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.models.price_candle import PriceCandle

#: Candles on each side of a candidate swing point (classic 5-candle fractal).
FRACTAL_WINDOW = 2


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    price: Decimal
    timestamp: datetime


def find_swing_points(
    candles: Sequence[PriceCandle], *, window: int = FRACTAL_WINDOW
) -> tuple[list[SwingPoint], list[SwingPoint]]:
    """Returns (swing_highs, swing_lows), oldest-first. `index` refers to
    the swing point's position within the provided `candles` sequence."""
    highs: list[SwingPoint] = []
    lows: list[SwingPoint] = []
    n = len(candles)

    for i in range(window, n - window):
        neighborhood = candles[i - window : i + window + 1]
        candle = candles[i]
        if candle.high == max(c.high for c in neighborhood):
            highs.append(SwingPoint(index=i, price=candle.high, timestamp=candle.timestamp))
        if candle.low == min(c.low for c in neighborhood):
            lows.append(SwingPoint(index=i, price=candle.low, timestamp=candle.timestamp))

    return highs, lows

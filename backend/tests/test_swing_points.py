from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.price_candle import PriceCandle
from app.services.market_structure.swing_points import find_swing_points

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _candles(highs: list[float], lows: list[float]) -> list[PriceCandle]:
    return [
        PriceCandle(
            timestamp=_BASE + timedelta(hours=i),
            open=Decimal(str(highs[i])),
            high=Decimal(str(highs[i])),
            low=Decimal(str(lows[i])),
            close=Decimal(str(lows[i])),
        )
        for i in range(len(highs))
    ]


def test_finds_swing_high_and_swing_low() -> None:
    highs = [1, 2, 3, 4, 3, 2, 1, 2, 3, 5, 3, 2, 1]
    lows = [10, 9, 8, 7, 6, 5, -4, 5, 6, 7, 8, 9, 10]
    candles = _candles(highs, lows)

    swing_highs, swing_lows = find_swing_points(candles)

    assert [h.index for h in swing_highs] == [3, 9]
    assert [float(h.price) for h in swing_highs] == [4, 5]
    assert [low.index for low in swing_lows] == [6]
    assert float(swing_lows[0].price) == -4


def test_no_swings_in_monotonic_series() -> None:
    highs = [float(i) for i in range(10)]
    lows = [float(i) - 1 for i in range(10)]
    candles = _candles(highs, lows)

    swing_highs, swing_lows = find_swing_points(candles)

    assert swing_highs == []
    assert swing_lows == []

"""docs/09 §6 Break of Structure: a bullish BOS is a candle *closing*
above the most recent still-unbroken swing high; a bearish BOS closes
below the most recent still-unbroken swing low. Once a swing level is
broken, the next BOS in that direction targets the next unbroken swing
level, not the same one again.

Strength is the percentage the close exceeded the broken level by -
a simple, deterministic magnitude measure that avoids coupling this
analyzer to Technical Analysis's ATR implementation (docs/43 §19).
"""

from collections.abc import Sequence

from app.models.price_candle import PriceCandle
from app.services.market_structure.swing_points import find_swing_points
from app.services.smc.types import BOSEvidence, Direction


def analyze(candles: Sequence[PriceCandle]) -> list[BOSEvidence]:
    swing_highs, swing_lows = find_swing_points(candles)
    events: list[BOSEvidence] = []
    broken_high_indices: set[int] = set()
    broken_low_indices: set[int] = set()

    for candle_idx, candle in enumerate(candles):
        candidate_highs = [
            h for h in swing_highs if h.index < candle_idx and h.index not in broken_high_indices
        ]
        if candidate_highs:
            level = candidate_highs[-1]
            if candle.close > level.price:
                strength = float(abs(candle.close - level.price) / level.price * 100)
                events.append(
                    BOSEvidence(
                        direction=Direction.BULLISH,
                        break_price=candle.close,
                        break_time=candle.timestamp,
                        strength=strength,
                        confirmed=True,
                    )
                )
                broken_high_indices.add(level.index)

        candidate_lows = [
            low
            for low in swing_lows
            if low.index < candle_idx and low.index not in broken_low_indices
        ]
        if candidate_lows:
            level = candidate_lows[-1]
            if candle.close < level.price:
                strength = float(abs(level.price - candle.close) / level.price * 100)
                events.append(
                    BOSEvidence(
                        direction=Direction.BEARISH,
                        break_price=candle.close,
                        break_time=candle.timestamp,
                        strength=strength,
                        confirmed=True,
                    )
                )
                broken_low_indices.add(level.index)

    return events

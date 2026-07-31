"""docs/16 §8 Breakout Detection: SMC's `BOSEvidence` already *is* the
"break of key level"/"close beyond resistance or support" requirement -
no separate break-detection logic. Only the most recent BOS, if it
occurred within the last few candles, is considered a live breakout
candidate; older BOS events are historical structure, not a "current"
breakout.
"""

from collections.abc import Sequence

from app.models.price_candle import PriceCandle
from app.services.market_regime.types import BreakoutDirection, BreakoutEvidence
from app.services.smc.types import BOSEvidence, Direction

_RECENCY_WINDOW = 3
_VOLUME_LOOKBACK = 20


def analyze(candles: Sequence[PriceCandle], bos_events: Sequence[BOSEvidence]) -> BreakoutEvidence:
    if not bos_events:
        return BreakoutEvidence(detected=False, direction=None, volume_confirmed=False)

    latest_bos = bos_events[-1]
    timestamp_to_index = {candle.timestamp: i for i, candle in enumerate(candles)}
    break_idx = timestamp_to_index.get(latest_bos.break_time)

    if break_idx is None or break_idx < len(candles) - _RECENCY_WINDOW:
        return BreakoutEvidence(detected=False, direction=None, volume_confirmed=False)

    break_candle = candles[break_idx]
    lookback = candles[max(0, break_idx - _VOLUME_LOOKBACK) : break_idx]
    volumes = [float(c.volume) for c in lookback if c.volume is not None]
    volume_confirmed = (
        break_candle.volume is not None
        and bool(volumes)
        and float(break_candle.volume) > (sum(volumes) / len(volumes))
    )

    subsequent = candles[break_idx + 1 :]
    reversed_back = any(
        (latest_bos.direction == Direction.BULLISH and candle.close < latest_bos.break_price)
        or (latest_bos.direction == Direction.BEARISH and candle.close > latest_bos.break_price)
        for candle in subsequent
    )

    if reversed_back:
        direction = BreakoutDirection.FALSE_BREAKOUT
    elif latest_bos.direction == Direction.BULLISH:
        direction = BreakoutDirection.BULLISH
    else:
        direction = BreakoutDirection.BEARISH

    return BreakoutEvidence(detected=True, direction=direction, volume_confirmed=volume_confirmed)

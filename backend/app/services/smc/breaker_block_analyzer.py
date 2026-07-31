"""docs/09 §13 Breaker Blocks: consumes `OrderBlockAnalyzer`'s evidence.
An order block is "broken" (invalidated) when a later candle *closes*
beyond its far side - for a bullish OB, closing below `zone_low`; for a
bearish OB, closing above `zone_high`. If price later retests that same
zone from the new direction, the zone becomes a confirmed "breaker" -
tracked as a status/flag on the same row, not a separate event type
(ADR-034).
"""

from collections.abc import Sequence

from app.models.enums import SMCEventStatus
from app.models.price_candle import PriceCandle
from app.services.smc.types import Direction, OrderBlockEvidence


def analyze(
    candles: Sequence[PriceCandle], order_blocks: Sequence[OrderBlockEvidence]
) -> list[OrderBlockEvidence]:
    for order_block in order_blocks:
        if order_block.status == SMCEventStatus.ARCHIVED:
            continue

        subsequent = [c for c in candles if c.timestamp > order_block.created_at]
        break_index: int | None = None

        for i, candle in enumerate(subsequent):
            if order_block.direction == Direction.BULLISH and candle.close < order_block.zone_low:
                break_index = i
                break
            if order_block.direction == Direction.BEARISH and candle.close > order_block.zone_high:
                break_index = i
                break

        if break_index is None:
            continue

        order_block.broken = True
        order_block.status = SMCEventStatus.INVALIDATED

        retested_since: bool = False
        for candle in subsequent[break_index + 1 :]:
            retested = candle.low <= order_block.zone_high and candle.high >= order_block.zone_low
            if retested:
                order_block.is_breaker = True
                order_block.retest_count += 1
                retested_since = True
                continue

            if not retested_since:
                continue

            continuation = (
                candle.close < order_block.zone_low
                if order_block.direction == Direction.BULLISH
                else candle.close > order_block.zone_high
            )
            if continuation:
                order_block.breaker_confirmed = True
                retested_since = False

    return list(order_blocks)

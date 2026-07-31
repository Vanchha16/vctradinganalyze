"""docs/09 §12 Mitigation Blocks: consumes `OrderBlockAnalyzer`'s
evidence (not raw candles) rather than re-scanning for new zones -
it only checks whether later candles interact with already-detected
zones. "Touched" = a wick re-enters the zone; "Mitigated" = a candle
*closes* within the zone after formation.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.models.price_candle import PriceCandle
from app.services.smc.types import OrderBlockEvidence


def _overlaps_zone(candle: PriceCandle, zone_low: Decimal, zone_high: Decimal) -> bool:
    return candle.low <= zone_high and candle.high >= zone_low


def _closes_within_zone(candle: PriceCandle, zone_low: Decimal, zone_high: Decimal) -> bool:
    return zone_low <= candle.close <= zone_high


def analyze(
    candles: Sequence[PriceCandle], order_blocks: Sequence[OrderBlockEvidence]
) -> list[OrderBlockEvidence]:
    for order_block in order_blocks:
        if order_block.status != SMCEventStatus.ACTIVE:
            continue

        subsequent = [c for c in candles if c.timestamp > order_block.created_at]
        for candle in subsequent:
            if _overlaps_zone(candle, order_block.zone_low, order_block.zone_high):
                order_block.touched = True
            if _closes_within_zone(candle, order_block.zone_low, order_block.zone_high):
                order_block.mitigated = True
                order_block.status = SMCEventStatus.MITIGATED

    return list(order_blocks)

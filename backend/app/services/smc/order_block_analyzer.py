"""docs/09 §8 Order Blocks (candle-pattern definition per ADR-034): the
last opposite-colored candle before the displacement move that produces
a BOS. For a bullish BOS, that's the last bearish (close < open) candle
before the break; for a bearish BOS, the last bullish candle.

Strength/freshness/volume-confirmation use simple, deterministic
heuristics documented in docs/43 §19 rather than reusing Technical
Analysis's ATR/volume indicators, to keep this analyzer decoupled.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.models.price_candle import PriceCandle
from app.services.smc import bos_analyzer
from app.services.smc.types import Direction, OrderBlockEvidence

_LOOKBACK_LIMIT = 10
_FRESHNESS_WINDOW_CANDLES = 50
_VOLUME_LOOKBACK = 20


def _is_bearish(candle: PriceCandle) -> bool:
    return candle.close < candle.open


def _is_bullish(candle: PriceCandle) -> bool:
    return candle.close > candle.open


def _find_order_block_candle_index(
    candles: Sequence[PriceCandle], break_idx: int, direction: Direction
) -> int | None:
    predicate = _is_bearish if direction == Direction.BULLISH else _is_bullish
    start = max(0, break_idx - _LOOKBACK_LIMIT)
    for i in range(break_idx - 1, start - 1, -1):
        if predicate(candles[i]):
            return i
    return None


def _volume_confirmed(candles: Sequence[PriceCandle], ob_idx: int) -> bool:
    candle = candles[ob_idx]
    if candle.volume is None:
        return False
    lookback_start = max(0, ob_idx - _VOLUME_LOOKBACK)
    prior = candles[lookback_start:ob_idx]
    volumes = [c.volume for c in prior if c.volume is not None]
    if not volumes:
        return False
    average = sum(volumes) / Decimal(len(volumes))
    return candle.volume > average


def analyze(candles: Sequence[PriceCandle]) -> list[OrderBlockEvidence]:
    if not candles:
        return []

    timestamp_to_index = {candle.timestamp: i for i, candle in enumerate(candles)}
    bos_events = bos_analyzer.analyze(candles)
    last_index = len(candles) - 1

    order_blocks: list[OrderBlockEvidence] = []
    seen_ob_indices: set[tuple[Direction, int]] = set()

    for bos in bos_events:
        break_idx = timestamp_to_index.get(bos.break_time)
        if break_idx is None:
            continue

        ob_idx = _find_order_block_candle_index(candles, break_idx, bos.direction)
        if ob_idx is None:
            continue
        if (bos.direction, ob_idx) in seen_ob_indices:
            continue
        seen_ob_indices.add((bos.direction, ob_idx))

        ob_candle = candles[ob_idx]
        zone_high = ob_candle.high
        zone_low = ob_candle.low
        zone_range = zone_high - zone_low

        displacement = abs(bos.break_price - zone_high)
        strength_score = float(displacement / zone_range) if zone_range > 0 else 0.0

        candles_since_creation = last_index - ob_idx
        freshness_score = max(0.0, 1.0 - (candles_since_creation / _FRESHNESS_WINDOW_CANDLES))

        order_blocks.append(
            OrderBlockEvidence(
                direction=bos.direction,
                zone_high=zone_high,
                zone_low=zone_low,
                created_at=ob_candle.timestamp,
                status=SMCEventStatus.ACTIVE,
                touched=False,
                mitigated=False,
                broken=False,
                strength_score=strength_score,
                freshness_score=freshness_score,
                volume_confirmed=_volume_confirmed(candles, ob_idx),
            )
        )

    return order_blocks

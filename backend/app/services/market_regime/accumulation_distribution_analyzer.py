"""docs/16 §9/§10 Accumulation/Distribution: a deterministic definition
(ADR-040) since docs/16 only gives characteristics, not an algorithm.

"Institutional Buying/Selling Evidence" is read directly off SMC's
already-persisted evidence rather than re-scanning candles: an ACTIVE
bullish Order Block, or a **sell-side** liquidity sweep (smart money
buying from stops beneath the range low), are accumulation signals; an
ACTIVE bearish Order Block, or a **buy-side** liquidity sweep (smart
money selling into stops above the range high), are distribution
signals - the standard ICT interpretation of a sweep's directionality.
"""

from collections.abc import Sequence

from app.models.enums import SMCEventStatus
from app.models.price_candle import PriceCandle
from app.services.market_regime.types import AccumulationDistributionEvidence, RangeEvidence
from app.services.smc.types import (
    Direction,
    LiquiditySide,
    LiquiditySweepEvidence,
    OrderBlockEvidence,
)

_RANGING_WEIGHT = 40.0
_VOLUME_WEIGHT = 30.0
_STRUCTURE_WEIGHT = 30.0
_VOLUME_INCREASE_RATIO = 1.1
_MIN_CANDLES_FOR_VOLUME_TREND = 20


def _volume_increasing(candles: Sequence[PriceCandle]) -> bool:
    volumes = [float(c.volume) for c in candles if c.volume is not None]
    if len(volumes) < _MIN_CANDLES_FOR_VOLUME_TREND:
        return False
    midpoint = len(volumes) // 2
    baseline_average = sum(volumes[:midpoint]) / midpoint
    recent_average = sum(volumes[midpoint:]) / (len(volumes) - midpoint)
    return baseline_average > 0 and (recent_average / baseline_average) > _VOLUME_INCREASE_RATIO


def analyze(
    candles: Sequence[PriceCandle],
    range_evidence: RangeEvidence,
    order_blocks: Sequence[OrderBlockEvidence],
    liquidity_sweeps: Sequence[LiquiditySweepEvidence],
) -> AccumulationDistributionEvidence:
    volume_increasing = _volume_increasing(candles)

    bullish_ob = any(
        ob.direction == Direction.BULLISH and ob.status == SMCEventStatus.ACTIVE
        for ob in order_blocks
    )
    bearish_ob = any(
        ob.direction == Direction.BEARISH and ob.status == SMCEventStatus.ACTIVE
        for ob in order_blocks
    )
    sell_side_sweep = any(s.side == LiquiditySide.SELL_SIDE for s in liquidity_sweeps)
    buy_side_sweep = any(s.side == LiquiditySide.BUY_SIDE for s in liquidity_sweeps)

    accumulation_score = (
        (_RANGING_WEIGHT if range_evidence.is_ranging else 0.0)
        + (_VOLUME_WEIGHT if volume_increasing else 0.0)
        + (_STRUCTURE_WEIGHT if (bullish_ob or sell_side_sweep) else 0.0)
    )
    distribution_score = (
        (_RANGING_WEIGHT if range_evidence.is_ranging else 0.0)
        + (_VOLUME_WEIGHT if volume_increasing else 0.0)
        + (_STRUCTURE_WEIGHT if (bearish_ob or buy_side_sweep) else 0.0)
    )

    return AccumulationDistributionEvidence(
        accumulation_score=min(100.0, accumulation_score),
        distribution_score=min(100.0, distribution_score),
    )

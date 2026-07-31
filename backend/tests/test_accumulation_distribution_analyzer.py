from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.services.market_regime import accumulation_distribution_analyzer
from app.services.market_regime.types import RangeEvidence
from app.services.smc.types import (
    Direction,
    LiquiditySide,
    LiquiditySweepEvidence,
    OrderBlockEvidence,
)
from tests.smc_helpers import make_candle

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_RANGING = RangeEvidence(is_ranging=True, range_width=Decimal("2"), range_strength="moderate")
_NOT_RANGING = RangeEvidence(is_ranging=False, range_width=None, range_strength=None)


def _order_block(direction: Direction) -> OrderBlockEvidence:
    return OrderBlockEvidence(
        direction=direction,
        zone_high=Decimal("12"),
        zone_low=Decimal("10"),
        created_at=_NOW,
        status=SMCEventStatus.ACTIVE,
        touched=False,
        mitigated=False,
        broken=False,
        strength_score=0.5,
        freshness_score=1.0,
        volume_confirmed=True,
    )


def _increasing_volume_candles() -> list:
    return [make_candle(i, 100, 101, 99, 100, volume=1000.0) for i in range(20)] + [
        make_candle(20 + i, 100, 101, 99, 100, volume=2000.0) for i in range(20)
    ]


def test_bullish_order_block_and_ranging_scores_accumulation_higher() -> None:
    candles = _increasing_volume_candles()
    order_blocks = [_order_block(Direction.BULLISH)]

    evidence = accumulation_distribution_analyzer.analyze(candles, _RANGING, order_blocks, [])

    assert evidence.accumulation_score > evidence.distribution_score


def test_bearish_order_block_and_ranging_scores_distribution_higher() -> None:
    candles = _increasing_volume_candles()
    order_blocks = [_order_block(Direction.BEARISH)]

    evidence = accumulation_distribution_analyzer.analyze(candles, _RANGING, order_blocks, [])

    assert evidence.distribution_score > evidence.accumulation_score


def test_sell_side_sweep_favors_accumulation() -> None:
    candles = _increasing_volume_candles()
    sweeps = [
        LiquiditySweepEvidence(
            side=LiquiditySide.SELL_SIDE, level=Decimal("90"), sweep_time=_NOW, false_breakout=True
        )
    ]

    evidence = accumulation_distribution_analyzer.analyze(candles, _RANGING, [], sweeps)

    assert evidence.accumulation_score > evidence.distribution_score


def test_no_ranging_no_volume_trend_no_structure_scores_zero() -> None:
    candles = [make_candle(i, 100, 101, 99, 100, volume=1000.0) for i in range(10)]

    evidence = accumulation_distribution_analyzer.analyze(candles, _NOT_RANGING, [], [])

    assert evidence.accumulation_score == 0.0
    assert evidence.distribution_score == 0.0

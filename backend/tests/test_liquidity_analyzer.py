from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.price_candle import PriceCandle
from app.services.smc import liquidity_analyzer
from app.services.smc.types import LiquiditySide

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _candle(index: int, high: float, low: float) -> PriceCandle:
    mid = (high + low) / 2
    return PriceCandle(
        timestamp=_BASE + timedelta(hours=index),
        open=Decimal(str(mid)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(mid)),
    )


def test_equal_highs_form_a_buy_side_liquidity_zone() -> None:
    highs = [90, 95, 98, 100, 98, 95, 90, 95, 98, 100.03, 98, 95, 90]
    lows = [80, 79, 78, 77, 78, 79, 80, 79, 78, 77, 78, 79, 80]
    candles = [_candle(i, highs[i], lows[i]) for i in range(len(highs))]

    zones, sweeps = liquidity_analyzer.analyze(candles)

    buy_side = [z for z in zones if z.side == LiquiditySide.BUY_SIDE]
    assert len(buy_side) == 1
    assert buy_side[0].touch_count == 2
    assert float(buy_side[0].level) == 100.03
    assert sweeps == []


def test_liquidity_sweep_detected_when_wick_exceeds_then_closes_back_inside() -> None:
    highs = [90, 95, 98, 100, 98, 95, 90, 95, 98, 100.03, 98, 95, 90]
    lows = [80, 79, 78, 77, 78, 79, 80, 79, 78, 77, 78, 79, 80]
    candles = [_candle(i, highs[i], lows[i]) for i in range(len(highs))]

    # A later candle wicks above the 100.03 liquidity level but closes back below it.
    sweep_candle = PriceCandle(
        timestamp=_BASE + timedelta(hours=20),
        open=Decimal("99"),
        high=Decimal("101"),
        low=Decimal("98"),
        close=Decimal("99.5"),
    )
    candles.append(sweep_candle)

    zones, sweeps = liquidity_analyzer.analyze(candles)

    assert len(sweeps) == 1
    assert sweeps[0].side == LiquiditySide.BUY_SIDE
    assert sweeps[0].false_breakout is True


def test_no_zones_without_equal_levels() -> None:
    highs = [float(i) for i in range(10)]
    lows = [float(i) - 1 for i in range(10)]
    candles = [_candle(i, highs[i], lows[i]) for i in range(len(highs))]

    zones, sweeps = liquidity_analyzer.analyze(candles)

    assert zones == []
    assert sweeps == []

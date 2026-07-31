import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.price_candle import PriceCandle
from app.services.smc import choch_analyzer
from app.services.smc.types import MarketStructureState

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _segment(
    start_index: int, count: int, start_price: float, drift_per_step: float, cycle: int = 24
):
    candles = []
    for i in range(count):
        idx = start_index + i
        base = start_price + drift_per_step * i
        osc = math.sin(2 * math.pi * i / cycle) * 5
        mid = base + osc
        candles.append(
            PriceCandle(
                timestamp=_BASE + timedelta(hours=idx),
                open=Decimal(str(mid)),
                high=Decimal(str(mid + 1)),
                low=Decimal(str(mid - 1)),
                close=Decimal(str(mid)),
            )
        )
    return candles, base


def test_choch_detected_on_uptrend_to_downtrend_reversal() -> None:
    up_candles, last_price = _segment(0, 150, 100.0, drift_per_step=0.3)
    down_candles, _ = _segment(150, 150, last_price, drift_per_step=-0.3)
    candles = up_candles + down_candles

    events = choch_analyzer.analyze(candles)

    assert len(events) >= 1
    first = events[0]
    assert first.previous_trend == MarketStructureState.BULLISH
    assert first.new_trend == MarketStructureState.BEARISH
    assert 0.0 <= first.confidence <= 1.0


def test_no_choch_in_pure_uptrend() -> None:
    candles, _ = _segment(0, 150, 100.0, drift_per_step=0.3)

    events = choch_analyzer.analyze(candles)

    assert events == []

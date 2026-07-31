from app.models.enums import SMCEventStatus
from app.services.smc import order_block_analyzer
from app.services.smc.types import Direction
from tests.smc_helpers import make_candles


def test_bullish_order_block_is_last_bearish_candle_before_bos() -> None:
    specs = [
        (5, 6, 4, 5),
        (6, 8, 5, 7),
        (7, 9, 6, 8),
        (8, 10, 7, 9),  # swing high (10)
        (8, 9, 6, 7),  # bearish
        (7, 8, 5, 6),  # bearish
        (6, 7, 4, 5),  # bearish
        (5, 6, 3, 4),  # bearish - last one before the BOS candle
        (5, 7, 4, 6),  # bullish
        (6, 12, 5, 11),  # BOS candle: closes above 10
    ]
    candles = make_candles(specs)

    order_blocks = order_block_analyzer.analyze(candles)

    assert len(order_blocks) == 1
    ob = order_blocks[0]
    assert ob.direction == Direction.BULLISH
    assert float(ob.zone_high) == 6.0
    assert float(ob.zone_low) == 3.0
    assert ob.status == SMCEventStatus.ACTIVE
    assert ob.touched is False
    assert ob.mitigated is False
    assert ob.broken is False
    assert 0.0 <= ob.freshness_score <= 1.0


def test_no_order_block_without_a_bos() -> None:
    specs = [(10, 11, 9, 10) for _ in range(10)]
    candles = make_candles(specs)

    assert order_block_analyzer.analyze(candles) == []

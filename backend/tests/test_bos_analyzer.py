from app.services.smc import bos_analyzer
from app.services.smc.types import Direction
from tests.smc_helpers import make_candles


def test_bullish_bos_when_close_breaks_above_swing_high() -> None:
    # Rises to a swing high of 10 at index 3, pulls back, then a later
    # candle closes above 10 - a bullish BOS.
    specs = [
        (5, 6, 4, 5),
        (6, 8, 5, 7),
        (7, 9, 6, 8),
        (8, 10, 7, 9),  # swing high candidate (needs neighbors both sides)
        (8, 9, 6, 7),
        (7, 8, 5, 6),
        (6, 7, 4, 5),
        (5, 6, 3, 4),
        (5, 7, 4, 6),
        (6, 12, 5, 11),  # closes (11) above the swing high (10) -> bullish BOS
    ]
    candles = make_candles(specs)

    events = bos_analyzer.analyze(candles)

    assert len(events) == 1
    assert events[0].direction == Direction.BULLISH
    assert float(events[0].break_price) == 11.0
    assert events[0].confirmed is True


def test_bearish_bos_when_close_breaks_below_swing_low() -> None:
    specs = [
        (10, 11, 9, 10),
        (9, 10, 7, 8),
        (8, 9, 6, 7),
        (7, 8, 5, 6),  # swing low candidate (low=5)
        (7, 9, 6, 8),
        (8, 10, 7, 9),
        (9, 11, 8, 10),
        (10, 12, 9, 11),
        (9, 11, 8, 10),
        (8, 9, 2, 3),  # closes (3) below the swing low (5) -> bearish BOS
    ]
    candles = make_candles(specs)

    events = bos_analyzer.analyze(candles)

    assert len(events) == 1
    assert events[0].direction == Direction.BEARISH
    assert float(events[0].break_price) == 3.0


def test_no_bos_when_no_swing_broken() -> None:
    specs = [(10, 11, 9, 10) for _ in range(10)]
    candles = make_candles(specs)

    events = bos_analyzer.analyze(candles)

    assert events == []

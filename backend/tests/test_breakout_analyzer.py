from datetime import UTC, datetime
from decimal import Decimal

from app.services.market_regime import breakout_analyzer
from app.services.market_regime.types import BreakoutDirection
from app.services.smc.types import BOSEvidence, Direction
from tests.smc_helpers import make_candle

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def test_no_breakout_without_bos() -> None:
    candles = [make_candle(i, 100, 101, 99, 100) for i in range(10)]

    evidence = breakout_analyzer.analyze(candles, [])

    assert evidence.detected is False


def test_bullish_breakout_detected_with_volume_confirmation() -> None:
    candles = [make_candle(i, 100, 101, 99, 100, volume=1000.0) for i in range(19)]
    break_candle = make_candle(19, 100, 110, 99, 108, volume=5000.0)
    candles.append(break_candle)

    bos = BOSEvidence(
        direction=Direction.BULLISH,
        break_price=Decimal("108"),
        break_time=break_candle.timestamp,
        strength=5.0,
        confirmed=True,
    )

    evidence = breakout_analyzer.analyze(candles, [bos])

    assert evidence.detected is True
    assert evidence.direction == BreakoutDirection.BULLISH
    assert evidence.volume_confirmed is True


def test_false_breakout_when_price_reverses_back() -> None:
    candles = [make_candle(i, 100, 101, 99, 100, volume=1000.0) for i in range(19)]
    break_candle = make_candle(19, 100, 110, 99, 108, volume=1000.0)
    candles.append(break_candle)
    candles.append(
        make_candle(20, 108, 108, 95, 96, volume=1000.0)
    )  # reverses back below break_price

    bos = BOSEvidence(
        direction=Direction.BULLISH,
        break_price=Decimal("108"),
        break_time=break_candle.timestamp,
        strength=5.0,
        confirmed=True,
    )

    evidence = breakout_analyzer.analyze(candles, [bos])

    assert evidence.direction == BreakoutDirection.FALSE_BREAKOUT


def test_stale_bos_not_treated_as_current_breakout() -> None:
    candles = [make_candle(i, 100, 101, 99, 100, volume=1000.0) for i in range(30)]
    old_break_time = candles[5].timestamp

    bos = BOSEvidence(
        direction=Direction.BULLISH,
        break_price=Decimal("100"),
        break_time=old_break_time,
        strength=5.0,
        confirmed=True,
    )

    evidence = breakout_analyzer.analyze(candles, [bos])

    assert evidence.detected is False

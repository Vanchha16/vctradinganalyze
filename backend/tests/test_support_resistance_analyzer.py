import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.enums import Timeframe
from app.models.price_candle import PriceCandle
from app.services.technical_analysis import support_resistance_analyzer

_ASSET_ID = uuid.uuid4()


def _candle(day_offset: int, high: float, low: float, close: float) -> PriceCandle:
    return PriceCandle(
        asset_id=_ASSET_ID,
        timeframe=Timeframe.D1,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day_offset),
        open=Decimal(str(close)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
    )


def test_finds_swing_high_and_low_by_construction() -> None:
    # A clear peak at index 5 and a clear trough at index 10, surrounded
    # by monotonically increasing/decreasing neighbors on both sides.
    candles = [
        _candle(0, 100, 95, 98),
        _candle(1, 102, 97, 100),
        _candle(2, 104, 99, 102),
        _candle(3, 106, 101, 104),
        _candle(4, 108, 103, 106),
        _candle(5, 110, 105, 108),  # swing high
        _candle(6, 108, 103, 106),
        _candle(7, 106, 101, 104),
        _candle(8, 104, 99, 102),
        _candle(9, 102, 97, 100),
        _candle(10, 100, 90, 95),  # swing low
        _candle(11, 102, 97, 100),
        _candle(12, 104, 99, 102),
    ]

    evidence = support_resistance_analyzer.analyze(candles, candles, current_price=Decimal("101"))

    swing_high_prices = [
        lvl.price for lvl in evidence.resistance_levels if lvl.source == "swing_high"
    ]
    swing_low_prices = [lvl.price for lvl in evidence.support_levels if lvl.source == "swing_low"]
    assert Decimal("110") in swing_high_prices
    assert Decimal("90") in swing_low_prices


def test_nearest_support_and_resistance_are_closest_to_current_price() -> None:
    candles = [_candle(i, 100 + i, 90 + i, 95 + i) for i in range(20)]

    evidence = support_resistance_analyzer.analyze(candles, candles, current_price=Decimal("110"))

    assert evidence.nearest_resistance is not None
    assert evidence.nearest_resistance.price > Decimal("110")
    assert evidence.nearest_support is not None
    assert evidence.nearest_support.price < Decimal("110")


def test_daily_weekly_monthly_high_low_from_daily_candles() -> None:
    daily_candles = [_candle(i, 100 + i, 90, 95) for i in range(30)]

    evidence = support_resistance_analyzer.analyze(
        daily_candles, daily_candles, current_price=Decimal("50")
    )

    sources = {lvl.source for lvl in evidence.resistance_levels}
    assert "daily_high" in sources or "weekly_high" in sources or "monthly_high" in sources


def test_round_number_levels_are_magnitude_aware() -> None:
    forex_evidence = support_resistance_analyzer.analyze([], [], current_price=Decimal("1.1050"))
    gold_evidence = support_resistance_analyzer.analyze([], [], current_price=Decimal("2400"))

    forex_round = [lvl for lvl in forex_evidence.resistance_levels if lvl.source == "round_number"]
    gold_round = [lvl for lvl in gold_evidence.resistance_levels if lvl.source == "round_number"]

    assert forex_round
    assert gold_round
    # forex steps are tiny (~0.005), gold steps are much larger (~100)
    forex_step = forex_round[0].price - Decimal("1.1050")
    gold_step = gold_round[0].price - Decimal("2400")
    assert forex_step < Decimal("1")
    assert gold_step > Decimal("1")


def test_handles_no_candles_gracefully() -> None:
    evidence = support_resistance_analyzer.analyze([], [], current_price=Decimal("100"))

    assert evidence.nearest_support is None or evidence.nearest_support.source == "round_number"
    assert (
        evidence.nearest_resistance is not None
    )  # round numbers always available for a positive price

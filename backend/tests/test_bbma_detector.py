"""Tests for BBMA structure detection (docs/61, ADR-148).

Series are constructed by hand so each test asserts one rule in
isolation. The four tunable constants are invented (docs/61 §7.3), so
these tests pin *behaviour at those values* - if a constant is
recalibrated later, the expectations here are the record of what changed.
"""

from app.indicators.types import OHLCVSeries
from app.services.bbma import BBMADirection, BBMASetupKind, detect
from app.services.bbma.detector import (
    REVERSE_MIN_BODY_RATIO,
    _body_ratio,
    _is_retest,
    _is_reverse_candle,
    _marked_level,
)
from app.services.bbma.indicators import bollinger_series, wma_series


def _flat_series(n: int = 60, price: float = 100.0) -> OHLCVSeries:
    return OHLCVSeries(
        opens=[price] * n,
        highs=[price + 0.5] * n,
        lows=[price - 0.5] * n,
        closes=[price] * n,
        volumes=[100.0] * n,
    )


# --- indicators -------------------------------------------------------


def test_wma_weights_recent_values_more_heavily() -> None:
    """Linear Weighted, not simple: with weights 1..5 over 1..5 the
    result is 55/15, well above the simple mean of 3."""
    out = wma_series([1.0, 2.0, 3.0, 4.0, 5.0], 5)

    assert out[:4] == [None, None, None, None]
    assert out[4] is not None
    assert round(out[4], 6) == round(55 / 15, 6)


def test_wma_series_is_aligned_to_its_input() -> None:
    """Same length as the input, `None` before warm-up - so callers can
    index by candle position without offsetting."""
    values = [float(i) for i in range(10)]

    out = wma_series(values, 4)

    assert len(out) == len(values)
    assert out[:3] == [None, None, None]
    assert all(v is not None for v in out[3:])


def test_bollinger_series_matches_the_existing_latest_value_function() -> None:
    """Must agree with `app.indicators.volatility.bollinger_bands`, or
    BBMA and Technical Analysis would disagree about where a band sits."""
    from app.indicators.volatility import bollinger_bands

    closes = [100.0 + (i % 7) for i in range(40)]

    series_out = bollinger_series(closes, 20)
    latest = bollinger_bands(closes, 20)

    assert latest is not None
    assert series_out[-1] is not None
    for a, b in zip(series_out[-1], latest, strict=True):
        assert round(a, 9) == round(b, 9)


# --- reverse candle ---------------------------------------------------


def test_doji_is_not_a_reverse_candle() -> None:
    """A tiny body inside a wide range is indecision, not rejection -
    this is what REVERSE_MIN_BODY_RATIO exists to exclude."""
    assert _body_ratio(100.0, 105.0, 95.0, 100.1) < REVERSE_MIN_BODY_RATIO
    assert not _is_reverse_candle(
        BBMADirection.SELL, 100.0, 105.0, 95.0, 100.1, band_upper=104.0, band_lower=96.0
    )


def test_reverse_candle_must_close_back_inside_the_band() -> None:
    """The whole point of the reverse is that the excess is rejected. A
    strong bearish candle still closing above Top BB has not rejected
    anything."""
    assert not _is_reverse_candle(
        BBMADirection.SELL, 110.0, 111.0, 105.0, 106.0, band_upper=104.0, band_lower=96.0
    )
    assert _is_reverse_candle(
        BBMADirection.SELL, 110.0, 111.0, 102.0, 103.0, band_upper=104.0, band_lower=96.0
    )


def test_reverse_candle_must_oppose_the_move() -> None:
    """A bullish candle cannot end an up-move."""
    assert not _is_reverse_candle(
        BBMADirection.SELL, 100.0, 104.0, 99.0, 103.0, band_upper=105.0, band_lower=95.0
    )


def test_marked_level_uses_the_body_not_the_wick() -> None:
    """docs/61 §3.1 says "mark the highest body" - a wick would place the
    level where price never actually settled."""
    assert _marked_level(BBMADirection.SELL, open_=103.0, close=101.0) == 103.0
    assert _marked_level(BBMADirection.BUY, open_=99.0, close=101.0) == 99.0


# --- retest -----------------------------------------------------------


def test_retest_requires_closing_back_on_the_setup_side() -> None:
    """Reaching the level is not enough. A close *through* it is the
    setup failing, not a retest."""
    assert _is_retest(
        BBMADirection.SELL, high=103.0, low=99.0, close=101.0, level=103.0, tolerance=0.0
    )
    assert not _is_retest(
        BBMADirection.SELL, high=104.0, low=99.0, close=103.5, level=103.0, tolerance=0.0
    )


def test_retest_tolerance_admits_a_near_touch() -> None:
    """Exact touches are rare; the ATR-scaled tolerance is what makes the
    rule usable on both XAUUSD and EURUSD."""
    assert not _is_retest(
        BBMADirection.SELL, high=102.9, low=99.0, close=101.0, level=103.0, tolerance=0.0
    )
    assert _is_retest(
        BBMADirection.SELL, high=102.9, low=99.0, close=101.0, level=103.0, tolerance=0.5
    )


# --- detect() ---------------------------------------------------------


def test_detect_reports_insufficient_history_rather_than_failing() -> None:
    result = detect(_flat_series(n=10), symbol="XAUUSD", timeframe="h1")

    assert result.setups == []
    assert result.latest is None
    assert any("Insufficient history" in w for w in result.warnings)


def test_detect_finds_no_setup_in_a_flat_market() -> None:
    """No MA can leave the band when price never moves, so there is no
    Extreme and therefore nothing downstream."""
    result = detect(_flat_series(), symbol="XAUUSD", timeframe="h1")

    assert result.setups == []
    assert any("No BBMA Extreme" in w for w in result.warnings)


def _spike_then_reject_series() -> OHLCVSeries:
    """Quiet base, a sharp rally that pushes MA5H outside the Top BB
    (Extreme SELL), a decisive bearish rejection candle, then a pullback
    that returns to test the rejection body and closes below it."""
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []

    for _ in range(30):  # quiet base to establish a narrow band
        opens.append(100.0)
        highs.append(100.3)
        lows.append(99.7)
        closes.append(100.0)

    price = 100.0
    for _ in range(6):  # rally - drags MA5H out of the band
        opens.append(price)
        price += 3.0
        highs.append(price + 0.5)
        lows.append(opens[-1] - 0.2)
        closes.append(price)

    # Decisive bearish rejection, closing well back down.
    opens.append(price)
    highs.append(price + 0.4)
    lows.append(price - 4.0)
    closes.append(price - 3.5)
    reject_body_top = price

    price -= 3.5
    for _ in range(3):  # drift down, away from the level
        opens.append(price)
        price -= 0.5
        highs.append(opens[-1] + 0.2)
        lows.append(price - 0.2)
        closes.append(price)

    # Pull back up to the marked body and close below it - the retest.
    opens.append(price)
    highs.append(reject_body_top + 0.05)
    lows.append(price - 0.2)
    closes.append(reject_body_top - 2.0)

    return OHLCVSeries(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=[100.0] * len(opens),
    )


def test_detect_finds_a_sell_extreme_with_reverse_and_retest() -> None:
    """The full docs/61 §3.1 sequence end to end: MA5H leaves the Top BB,
    a reverse candle stops the move, price retests its body."""
    result = detect(_spike_then_reject_series(), symbol="XAUUSD", timeframe="h1")

    assert result.setups, f"expected a setup; warnings={result.warnings}"
    setup = result.latest
    assert setup is not None
    assert setup.kind is BBMASetupKind.EXTREME
    assert setup.direction is BBMADirection.SELL
    assert setup.marked_level is not None

    # Entry is the MA5/10 band, never the marked level itself (docs/61 §2).
    assert setup.entry_price != setup.marked_level
    # A sell is invalidated above; the target sits below.
    assert setup.stop_loss > setup.entry_price
    assert setup.take_profit < setup.stop_loss
    assert any("CS Reverse" in note for note in setup.notes)
    assert any("CS Retest" in note for note in setup.notes)


def test_detect_reports_conditions_at_the_latest_bar() -> None:
    result = detect(_spike_then_reject_series(), symbol="XAUUSD", timeframe="h1")

    assert result.conditions is not None
    assert isinstance(result.conditions.csm, bool)
    assert isinstance(result.conditions.zzl, bool)
    assert result.conditions.trend_major in (BBMADirection.BUY, BBMADirection.SELL, None)

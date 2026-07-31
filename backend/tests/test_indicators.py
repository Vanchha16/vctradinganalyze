import math

import pytest

from app.indicators import registry
from app.indicators.momentum import cci, macd, momentum, rsi, stochastic_rsi
from app.indicators.trend import ema, sma
from app.indicators.trend_strength import adx
from app.indicators.volatility import atr, bollinger_bands, standard_deviation
from app.indicators.volume import obv, relative_volume, volume_sma, vwap


def test_sma_linear_series() -> None:
    values = [float(i) for i in range(1, 11)]  # 1..10
    assert sma(values, 5) == pytest.approx(8.0)


def test_sma_insufficient_data_returns_none() -> None:
    assert sma([1.0, 2.0], 5) is None


def test_ema_converges_to_sma_on_linear_series() -> None:
    values = [float(i) for i in range(1, 11)]  # 1..10
    assert ema(values, 5) == pytest.approx(8.0)


def test_rsi_is_100_for_strictly_increasing_prices() -> None:
    values = [float(i) for i in range(1, 30)]
    assert rsi(values, 14) == pytest.approx(100.0)


def test_rsi_is_0_for_strictly_decreasing_prices() -> None:
    values = [float(i) for i in range(30, 1, -1)]
    assert rsi(values, 14) == pytest.approx(0.0)


def test_rsi_insufficient_data_returns_none() -> None:
    assert rsi([1.0, 2.0, 3.0], 14) is None


def test_macd_is_positive_for_strong_uptrend() -> None:
    values = [float(i) for i in range(1, 60)]
    result = macd(values)
    assert result is not None
    macd_value, _signal, _histogram = result
    assert macd_value > 0


def test_macd_insufficient_data_returns_none() -> None:
    assert macd([float(i) for i in range(1, 10)]) is None


def test_stochastic_rsi_is_zero_when_rsi_is_flat_at_ceiling() -> None:
    values = [float(i) for i in range(1, 40)]  # strictly increasing -> RSI pinned at 100
    assert stochastic_rsi(values, 14) == pytest.approx(0.0)


def test_cci_is_zero_for_flat_prices() -> None:
    highs = [10.0] * 25
    lows = [10.0] * 25
    closes = [10.0] * 25
    assert cci(highs, lows, closes, 20) == pytest.approx(0.0)


def test_momentum_arithmetic_sequence() -> None:
    values = [float(i) for i in range(1, 50)]
    assert momentum(values, 10) == pytest.approx(10.0)


def test_momentum_insufficient_data_returns_none() -> None:
    assert momentum([1.0, 2.0], 10) is None


def test_atr_is_zero_for_flat_prices() -> None:
    highs = [10.0] * 20
    lows = [10.0] * 20
    closes = [10.0] * 20
    assert atr(highs, lows, closes, 14) == pytest.approx(0.0)


def test_bollinger_bands_collapse_for_flat_prices() -> None:
    closes = [10.0] * 25
    result = bollinger_bands(closes, 20, 2.0)
    assert result is not None
    upper, middle, lower = result
    assert upper == pytest.approx(10.0)
    assert middle == pytest.approx(10.0)
    assert lower == pytest.approx(10.0)


def test_standard_deviation_is_zero_for_flat_prices() -> None:
    assert standard_deviation([10.0] * 25, 20) == pytest.approx(0.0)


def test_vwap_matches_hand_computed_value() -> None:
    highs = [10.0, 20.0]
    lows = [10.0, 20.0]
    closes = [10.0, 20.0]
    volumes: list[float | None] = [100.0, 300.0]
    # typical prices: 10 and 20; (10*100 + 20*300) / 400 = 17.5
    assert vwap(highs, lows, closes, volumes) == pytest.approx(17.5)


def test_obv_matches_hand_computed_running_total() -> None:
    closes = [10.0, 11.0, 10.0, 12.0]
    volumes: list[float | None] = [100.0, 200.0, 150.0, 300.0]
    # +200 (up), -150 (down), +300 (up) = 350
    assert obv(closes, volumes) == pytest.approx(350.0)


def test_volume_sma_matches_hand_computed_value() -> None:
    volumes: list[float | None] = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert volume_sma(volumes, 3) == pytest.approx(40.0)


def test_relative_volume_matches_hand_computed_value() -> None:
    volumes: list[float | None] = [10.0, 10.0, 10.0, 10.0, 20.0]
    assert relative_volume(volumes, 4) == pytest.approx(2.0)


def test_adx_insufficient_data_returns_none() -> None:
    assert adx([10.0, 11.0], [9.0, 10.0], [9.5, 10.5], 14) is None


def test_adx_shows_stronger_plus_di_in_uptrend() -> None:
    n = 60
    closes = [100.0 + i for i in range(n)]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]

    result = adx(highs, lows, closes, 14)
    assert result is not None
    adx_value, di_plus, di_minus = result
    assert 0.0 <= adx_value <= 100.0
    assert di_plus > di_minus


def test_registry_contains_every_docs_08_indicator() -> None:
    names = {spec.name for spec in registry.list_all()}
    expected = {
        "ema_20",
        "ema_50",
        "ema_100",
        "ema_200",
        "sma_200",
        "rsi_14",
        "macd",
        "stoch_rsi_14",
        "cci_20",
        "momentum_10",
        "atr_14",
        "bollinger_bands_20",
        "stddev_20",
        "vwap",
        "obv",
        "volume_sma_20",
        "relative_volume_20",
        "adx_14",
    }
    assert expected <= names


def test_registered_indicators_are_finite_on_enough_synthetic_data() -> None:
    from app.indicators.types import OHLCVSeries

    n = 260
    closes = [100.0 + math.sin(i / 10) * 5 for i in range(n)]
    series = OHLCVSeries(
        opens=closes,
        highs=[c + 1 for c in closes],
        lows=[c - 1 for c in closes],
        closes=closes,
        volumes=[1000.0 + i for i in range(n)],
    )

    for spec in registry.list_all():
        output = spec.func(series)
        assert output is not None, f"{spec.name} unexpectedly returned None"
        assert math.isfinite(output.value), f"{spec.name} produced a non-finite value"

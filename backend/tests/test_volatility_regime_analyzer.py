from app.services.market_regime import volatility_regime_analyzer
from app.services.market_regime.types import VolatilityRegimeState
from tests.smc_helpers import make_candles


def test_stable_range_classified_normal() -> None:
    specs = [(100, 101, 99, 100) for _ in range(60)]
    candles = make_candles(specs)

    evidence = volatility_regime_analyzer.analyze(candles)

    assert evidence.state == VolatilityRegimeState.NORMAL


def test_recent_expansion_classified_high_or_extreme() -> None:
    # Quiet for the first 40 candles, then a sudden burst of wide-range
    # candles at the end - recent ATR average rises sharply vs baseline.
    specs = [(100, 100.5, 99.5, 100) for _ in range(40)]
    specs += [(100, 110, 90, 105) for _ in range(20)]
    candles = make_candles(specs)

    evidence = volatility_regime_analyzer.analyze(candles)

    assert evidence.state in (VolatilityRegimeState.HIGH, VolatilityRegimeState.EXTREME)
    assert evidence.recent_atr_average is not None
    assert evidence.baseline_atr_average is not None
    assert evidence.recent_atr_average > evidence.baseline_atr_average


def test_recent_contraction_classified_low_or_very_low() -> None:
    specs = [(100, 110, 90, 105) for _ in range(40)]
    specs += [(100, 100.2, 99.8, 100) for _ in range(20)]
    candles = make_candles(specs)

    evidence = volatility_regime_analyzer.analyze(candles)

    assert evidence.state in (VolatilityRegimeState.LOW, VolatilityRegimeState.VERY_LOW)


def test_insufficient_candles_returns_normal_with_no_averages() -> None:
    candles = make_candles([(100, 101, 99, 100)])

    evidence = volatility_regime_analyzer.analyze(candles)

    assert evidence.state == VolatilityRegimeState.NORMAL
    assert evidence.recent_atr_average is None

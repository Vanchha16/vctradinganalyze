from app.indicators.types import IndicatorOutput
from app.services.technical_analysis import (
    conflict_analyzer,
    momentum_analyzer,
    moving_average_analyzer,
    oscillator_analyzer,
    trend_analyzer,
    volatility_analyzer,
    volume_analyzer,
)
from app.services.technical_analysis.types import (
    OscillatorState,
    TrendDirection,
    TrendStrengthLevel,
    VolatilityState,
    VolumeState,
)


def _bullish_indicators(adx: float = 30.0) -> dict[str, IndicatorOutput]:
    return {
        "ema_20": IndicatorOutput(value=110.0),
        "ema_50": IndicatorOutput(value=105.0),
        "ema_100": IndicatorOutput(value=100.0),
        "ema_200": IndicatorOutput(value=95.0),
        "sma_200": IndicatorOutput(value=94.0),
        "adx_14": IndicatorOutput(value=adx, metadata={"di_plus": 30.0, "di_minus": 10.0}),
    }


def _bearish_indicators(adx: float = 30.0) -> dict[str, IndicatorOutput]:
    return {
        "ema_20": IndicatorOutput(value=95.0),
        "ema_50": IndicatorOutput(value=100.0),
        "ema_100": IndicatorOutput(value=105.0),
        "ema_200": IndicatorOutput(value=110.0),
        "sma_200": IndicatorOutput(value=111.0),
        "adx_14": IndicatorOutput(value=adx, metadata={"di_plus": 10.0, "di_minus": 30.0}),
    }


# --- MovingAverageAnalyzer ---


def test_moving_average_bullish_alignment() -> None:
    evidence = moving_average_analyzer.analyze(_bullish_indicators(), current_price=115.0)

    assert evidence.bullish_alignment is True
    assert evidence.bearish_alignment is False
    assert evidence.alignment_score == 1.0
    assert evidence.price_above_ema20 is True


def test_moving_average_bearish_alignment() -> None:
    evidence = moving_average_analyzer.analyze(_bearish_indicators(), current_price=90.0)

    assert evidence.bearish_alignment is True
    assert evidence.bullish_alignment is False
    assert evidence.alignment_score == 0.0


def test_moving_average_missing_data_returns_none_facts() -> None:
    evidence = moving_average_analyzer.analyze({}, current_price=100.0)

    assert evidence.price_above_ema20 is None
    assert evidence.bullish_alignment is False
    assert evidence.alignment_score == 0.0


# --- TrendAnalyzer ---


def test_trend_analyzer_strong_bullish() -> None:
    evidence = trend_analyzer.analyze(_bullish_indicators(adx=45.0), current_price=115.0)

    assert evidence.direction == TrendDirection.BULLISH
    assert evidence.strength == TrendStrengthLevel.VERY_STRONG


def test_trend_analyzer_weak_adx_still_weak_strength() -> None:
    evidence = trend_analyzer.analyze(_bullish_indicators(adx=10.0), current_price=115.0)

    assert evidence.direction == TrendDirection.BULLISH
    assert evidence.strength == TrendStrengthLevel.WEAK


def test_trend_analyzer_sideways_when_mas_not_aligned() -> None:
    mixed = {
        "ema_20": IndicatorOutput(value=100.0),
        "ema_50": IndicatorOutput(value=105.0),
        "ema_100": IndicatorOutput(value=100.0),
        "ema_200": IndicatorOutput(value=110.0),
    }
    evidence = trend_analyzer.analyze(mixed, current_price=102.0)

    assert evidence.direction == TrendDirection.SIDEWAYS


def test_trend_analyzer_missing_adx_defaults_to_weak() -> None:
    indicators = {
        "ema_20": IndicatorOutput(value=110.0),
        "ema_50": IndicatorOutput(value=105.0),
        "ema_100": IndicatorOutput(value=100.0),
        "ema_200": IndicatorOutput(value=95.0),
    }
    evidence = trend_analyzer.analyze(indicators, current_price=115.0)

    assert evidence.strength == TrendStrengthLevel.WEAK
    assert evidence.adx is None


# --- MomentumAnalyzer ---


def test_momentum_analyzer_bullish_macd() -> None:
    indicators = {"macd": IndicatorOutput(value=1.5, metadata={"signal": 1.0, "histogram": 0.5})}
    evidence = momentum_analyzer.analyze(indicators)

    assert evidence.macd_bullish is True
    assert evidence.macd_histogram == 0.5


def test_momentum_analyzer_missing_indicators() -> None:
    evidence = momentum_analyzer.analyze({})

    assert evidence.macd_bullish is None
    assert evidence.momentum_positive is None


def test_momentum_analyzer_positive_momentum() -> None:
    evidence = momentum_analyzer.analyze({"momentum_10": IndicatorOutput(value=2.5)})

    assert evidence.momentum_positive is True


# --- OscillatorAnalyzer ---


def test_oscillator_analyzer_classifies_overbought_oversold_healthy() -> None:
    evidence = oscillator_analyzer.analyze(
        {
            "rsi_14": IndicatorOutput(value=75.0),
            "stoch_rsi_14": IndicatorOutput(value=15.0),
            "cci_20": IndicatorOutput(value=50.0),
        }
    )

    assert evidence.rsi_state == OscillatorState.OVERBOUGHT
    assert evidence.stoch_rsi_state == OscillatorState.OVERSOLD
    assert evidence.cci_state == OscillatorState.HEALTHY


def test_oscillator_analyzer_unavailable_when_missing() -> None:
    evidence = oscillator_analyzer.analyze({})

    assert evidence.rsi_state == OscillatorState.UNAVAILABLE


# --- VolatilityAnalyzer ---


def test_volatility_analyzer_detects_squeeze() -> None:
    indicators = {
        "bollinger_bands_20": IndicatorOutput(value=100.0, metadata={"upper": 100.5, "lower": 99.5})
    }
    evidence = volatility_analyzer.analyze(indicators, current_price=100.0)

    assert evidence.state == VolatilityState.SQUEEZE


def test_volatility_analyzer_near_upper_band() -> None:
    indicators = {
        "bollinger_bands_20": IndicatorOutput(value=100.0, metadata={"upper": 105.0, "lower": 95.0})
    }
    evidence = volatility_analyzer.analyze(indicators, current_price=106.0)

    assert evidence.state == VolatilityState.NEAR_UPPER_BAND


def test_volatility_analyzer_stable() -> None:
    indicators = {
        "bollinger_bands_20": IndicatorOutput(value=100.0, metadata={"upper": 105.0, "lower": 95.0})
    }
    evidence = volatility_analyzer.analyze(indicators, current_price=100.0)

    assert evidence.state == VolatilityState.STABLE


def test_volatility_analyzer_unavailable_when_missing() -> None:
    evidence = volatility_analyzer.analyze({}, current_price=100.0)

    assert evidence.state == VolatilityState.UNAVAILABLE


# --- VolumeAnalyzer ---


def test_volume_analyzer_price_above_vwap_and_high_relative_volume() -> None:
    indicators = {
        "vwap": IndicatorOutput(value=95.0),
        "relative_volume_20": IndicatorOutput(value=1.8),
    }
    evidence = volume_analyzer.analyze(indicators, current_price=100.0)

    assert evidence.price_above_vwap is True
    assert evidence.relative_volume_state == VolumeState.ABOVE_AVERAGE


def test_volume_analyzer_unavailable_when_missing() -> None:
    evidence = volume_analyzer.analyze({}, current_price=100.0)

    assert evidence.price_above_vwap is None
    assert evidence.relative_volume_state == VolumeState.UNAVAILABLE


# --- ConflictAnalyzer ---


def test_conflict_analyzer_detects_bullish_bearish_macd_conflict() -> None:
    trend = trend_analyzer.analyze(_bullish_indicators(adx=45.0), current_price=115.0)
    momentum = momentum_analyzer.analyze(
        {"macd": IndicatorOutput(value=0.5, metadata={"signal": 1.0, "histogram": -0.5})}
    )
    oscillator = oscillator_analyzer.analyze({})
    volume = volume_analyzer.analyze({}, current_price=115.0)

    report = conflict_analyzer.analyze(trend, momentum, oscillator, volume)

    assert len(report.conflicts) == 1
    assert "MACD is bearish" in report.conflicts[0].description


def test_conflict_analyzer_no_conflicts_when_everything_agrees() -> None:
    trend = trend_analyzer.analyze(_bullish_indicators(adx=45.0), current_price=115.0)
    momentum = momentum_analyzer.analyze(
        {"macd": IndicatorOutput(value=1.5, metadata={"signal": 1.0, "histogram": 0.5})}
    )
    oscillator = oscillator_analyzer.analyze({"rsi_14": IndicatorOutput(value=55.0)})
    volume = volume_analyzer.analyze({"vwap": IndicatorOutput(value=100.0)}, current_price=115.0)

    report = conflict_analyzer.analyze(trend, momentum, oscillator, volume)

    assert report.conflicts == []
    assert report.is_mixed is False


def test_conflict_analyzer_weak_trend_flagged() -> None:
    trend = trend_analyzer.analyze(_bullish_indicators(adx=5.0), current_price=115.0)
    momentum = momentum_analyzer.analyze({})
    oscillator = oscillator_analyzer.analyze({})
    volume = volume_analyzer.analyze({}, current_price=115.0)

    report = conflict_analyzer.analyze(trend, momentum, oscillator, volume)

    assert any("weak trend" in c.description for c in report.conflicts)

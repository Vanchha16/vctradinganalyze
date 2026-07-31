from decimal import Decimal

from app.services.technical_analysis import scoring_engine
from app.services.technical_analysis.types import (
    Conflict,
    ConflictReport,
    MomentumEvidence,
    MovingAverageEvidence,
    OscillatorEvidence,
    OscillatorState,
    SupportResistanceEvidence,
    SupportResistanceLevel,
    TrendDirection,
    TrendEvidence,
    TrendStrengthLevel,
    VolatilityEvidence,
    VolatilityState,
    VolumeEvidence,
    VolumeState,
)

_NO_CONFLICTS = ConflictReport(conflicts=[])


def _perfect_bullish_trend() -> TrendEvidence:
    ma = MovingAverageEvidence(
        price_above_ema20=True,
        price_above_ema50=True,
        price_above_ema100=True,
        price_above_ema200=True,
        price_above_sma200=True,
        bullish_alignment=True,
        bearish_alignment=False,
        alignment_score=1.0,
    )
    return TrendEvidence(
        direction=TrendDirection.BULLISH,
        strength=TrendStrengthLevel.VERY_STRONG,
        adx=45.0,
        di_plus=30.0,
        di_minus=10.0,
        moving_average=ma,
    )


def test_perfect_bullish_scenario_scores_near_maximum() -> None:
    trend = _perfect_bullish_trend()
    momentum = MomentumEvidence(
        macd=1.5,
        macd_signal=1.0,
        macd_histogram=0.5,
        macd_bullish=True,
        momentum=2.0,
        momentum_positive=True,
    )
    oscillator = OscillatorEvidence(
        rsi=55.0,
        rsi_state=OscillatorState.HEALTHY,
        stoch_rsi=50.0,
        stoch_rsi_state=OscillatorState.HEALTHY,
        cci=50.0,
        cci_state=OscillatorState.HEALTHY,
    )
    volume = VolumeEvidence(
        price_above_vwap=True,
        obv=1000.0,
        relative_volume=1.5,
        relative_volume_state=VolumeState.ABOVE_AVERAGE,
    )
    volatility = VolatilityEvidence(
        atr=1.0,
        bollinger_upper=110.0,
        bollinger_lower=90.0,
        stddev=1.0,
        state=VolatilityState.STABLE,
    )
    support_resistance = SupportResistanceEvidence(
        nearest_support=SupportResistanceLevel(
            price=Decimal("90"), source="swing_low", strength="weak"
        ),
        nearest_resistance=SupportResistanceLevel(
            price=Decimal("110"), source="swing_high", strength="weak"
        ),
    )

    breakdown = scoring_engine.score(
        trend, momentum, oscillator, volume, volatility, support_resistance, _NO_CONFLICTS
    )

    assert breakdown.total == 100.0
    assert breakdown.penalties == 0.0


def test_conflicts_apply_penalty_and_are_floored_at_zero() -> None:
    trend = _perfect_bullish_trend()
    momentum = MomentumEvidence(
        macd=None,
        macd_signal=None,
        macd_histogram=None,
        macd_bullish=None,
        momentum=None,
        momentum_positive=None,
    )
    oscillator = OscillatorEvidence(
        rsi=None,
        rsi_state=OscillatorState.UNAVAILABLE,
        stoch_rsi=None,
        stoch_rsi_state=OscillatorState.UNAVAILABLE,
        cci=None,
        cci_state=OscillatorState.UNAVAILABLE,
    )
    volume = VolumeEvidence(
        price_above_vwap=None,
        obv=None,
        relative_volume=None,
        relative_volume_state=VolumeState.UNAVAILABLE,
    )
    volatility = VolatilityEvidence(
        atr=None,
        bollinger_upper=None,
        bollinger_lower=None,
        stddev=None,
        state=VolatilityState.UNAVAILABLE,
    )
    support_resistance = SupportResistanceEvidence(nearest_support=None, nearest_resistance=None)

    many_conflicts = ConflictReport(conflicts=[Conflict(f"conflict {i}") for i in range(15)])

    breakdown = scoring_engine.score(
        trend, momentum, oscillator, volume, volatility, support_resistance, many_conflicts
    )

    assert breakdown.penalties == -150.0
    assert breakdown.total == 0.0  # floored, never negative


def test_score_breakdown_components_sum_to_total() -> None:
    trend = _perfect_bullish_trend()
    momentum = MomentumEvidence(
        macd=1.0,
        macd_signal=0.5,
        macd_histogram=0.5,
        macd_bullish=True,
        momentum=1.0,
        momentum_positive=True,
    )
    oscillator = OscillatorEvidence(
        rsi=55.0,
        rsi_state=OscillatorState.HEALTHY,
        stoch_rsi=50.0,
        stoch_rsi_state=OscillatorState.HEALTHY,
        cci=50.0,
        cci_state=OscillatorState.HEALTHY,
    )
    volume = VolumeEvidence(
        price_above_vwap=True,
        obv=100.0,
        relative_volume=1.2,
        relative_volume_state=VolumeState.ABOVE_AVERAGE,
    )
    volatility = VolatilityEvidence(
        atr=1.0,
        bollinger_upper=110.0,
        bollinger_lower=90.0,
        stddev=1.0,
        state=VolatilityState.STABLE,
    )
    support_resistance = SupportResistanceEvidence(nearest_support=None, nearest_resistance=None)
    conflicts = ConflictReport(conflicts=[Conflict("one conflict")])

    breakdown = scoring_engine.score(
        trend, momentum, oscillator, volume, volatility, support_resistance, conflicts
    )

    raw_sum = (
        breakdown.trend
        + breakdown.momentum
        + breakdown.oscillator
        + breakdown.volume
        + breakdown.volatility
        + breakdown.support_resistance
        + breakdown.penalties
    )
    assert breakdown.total == max(0.0, min(100.0, raw_sum))
    assert breakdown.penalties == -10.0

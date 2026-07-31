"""Definitive technical scoring formula (ADR-028), superseding docs/08 §9's
illustrative example (which only summed to 75, not its own stated max of
100). 100-point breakdown: trend alignment (25) + trend strength (15) +
momentum (15) + oscillator (15) + volume (15) + volatility (10) +
support/resistance (5) = 100, minus a fixed penalty per detected conflict.
"""

from app.services.technical_analysis.types import (
    ConflictReport,
    MomentumEvidence,
    OscillatorEvidence,
    OscillatorState,
    ScoreBreakdown,
    SupportResistanceEvidence,
    TrendDirection,
    TrendEvidence,
    TrendStrengthLevel,
    VolatilityEvidence,
    VolatilityState,
    VolumeEvidence,
)

_TREND_ALIGNMENT_MAX = 25.0
_TREND_STRENGTH_MAX = 15.0
_MOMENTUM_MAX = 15.0
_OSCILLATOR_MAX = 15.0
_VOLUME_MAX = 15.0
_VOLATILITY_MAX = 10.0
_SUPPORT_RESISTANCE_MAX = 5.0
_CONFLICT_PENALTY = 10.0

_STRENGTH_WEIGHT = {
    TrendStrengthLevel.VERY_STRONG: 1.0,
    TrendStrengthLevel.STRONG: 0.8,
    TrendStrengthLevel.MODERATE: 0.4,
    TrendStrengthLevel.WEAK: 0.0,
}

_VOLATILITY_WEIGHT = {
    VolatilityState.STABLE: 1.0,
    VolatilityState.SQUEEZE: 0.5,
    VolatilityState.NEAR_UPPER_BAND: 0.5,
    VolatilityState.NEAR_LOWER_BAND: 0.5,
    VolatilityState.UNAVAILABLE: 0.5,
}


def _trend_score(trend: TrendEvidence) -> float:
    alignment = trend.moving_average.alignment_score * _TREND_ALIGNMENT_MAX
    strength = _STRENGTH_WEIGHT[trend.strength] * _TREND_STRENGTH_MAX
    return alignment + strength


def _momentum_score(direction: TrendDirection, momentum: MomentumEvidence) -> float:
    if direction == TrendDirection.SIDEWAYS or momentum.macd_bullish is None:
        return _MOMENTUM_MAX * 0.5
    agrees = (direction == TrendDirection.BULLISH) == momentum.macd_bullish
    return _MOMENTUM_MAX if agrees else 0.0


def _oscillator_score(oscillator: OscillatorEvidence) -> float:
    if oscillator.rsi_state == OscillatorState.HEALTHY:
        return _OSCILLATOR_MAX
    return _OSCILLATOR_MAX * 0.5


def _volume_score(direction: TrendDirection, volume: VolumeEvidence) -> float:
    if direction == TrendDirection.SIDEWAYS or volume.price_above_vwap is None:
        return _VOLUME_MAX * 0.5
    agrees = (direction == TrendDirection.BULLISH) == volume.price_above_vwap
    return _VOLUME_MAX if agrees else 0.0


def _volatility_score(volatility: VolatilityEvidence) -> float:
    return _VOLATILITY_WEIGHT[volatility.state] * _VOLATILITY_MAX


def _support_resistance_score(support_resistance: SupportResistanceEvidence) -> float:
    has_support = support_resistance.nearest_support is not None
    has_resistance = support_resistance.nearest_resistance is not None
    if has_support and has_resistance:
        return _SUPPORT_RESISTANCE_MAX
    if has_support or has_resistance:
        return _SUPPORT_RESISTANCE_MAX * 0.5
    return 0.0


def _penalties(conflicts: ConflictReport) -> float:
    return -_CONFLICT_PENALTY * len(conflicts.conflicts)


def score(
    trend: TrendEvidence,
    momentum: MomentumEvidence,
    oscillator: OscillatorEvidence,
    volume: VolumeEvidence,
    volatility: VolatilityEvidence,
    support_resistance: SupportResistanceEvidence,
    conflicts: ConflictReport,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        trend=_trend_score(trend),
        momentum=_momentum_score(trend.direction, momentum),
        oscillator=_oscillator_score(oscillator),
        volume=_volume_score(trend.direction, volume),
        volatility=_volatility_score(volatility),
        support_resistance=_support_resistance_score(support_resistance),
        penalties=_penalties(conflicts),
    )

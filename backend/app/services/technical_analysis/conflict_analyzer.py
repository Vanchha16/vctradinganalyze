"""docs/08 §10 Conflict Detection - inspects every analyzer's evidence for
contradictions, consumed by TechnicalScoringEngine for score penalties
and trend-verdict relabeling (docs/42 §7)."""

from app.services.technical_analysis.types import (
    Conflict,
    ConflictReport,
    MomentumEvidence,
    OscillatorEvidence,
    OscillatorState,
    TrendDirection,
    TrendEvidence,
    TrendStrengthLevel,
    VolumeEvidence,
)


def analyze(
    trend: TrendEvidence,
    momentum: MomentumEvidence,
    oscillator: OscillatorEvidence,
    volume: VolumeEvidence,
) -> ConflictReport:
    conflicts: list[Conflict] = []

    if trend.direction == TrendDirection.BULLISH and momentum.macd_bullish is False:
        conflicts.append(Conflict("Bullish trend but MACD is bearish"))
    if trend.direction == TrendDirection.BEARISH and momentum.macd_bullish is True:
        conflicts.append(Conflict("Bearish trend but MACD is bullish"))

    if trend.direction != TrendDirection.SIDEWAYS and trend.strength == TrendStrengthLevel.WEAK:
        conflicts.append(
            Conflict(f"{trend.direction.value.capitalize()} trend but ADX indicates a weak trend")
        )

    if (
        trend.direction == TrendDirection.BULLISH
        and oscillator.rsi_state == OscillatorState.OVERBOUGHT
    ):
        conflicts.append(Conflict("Bullish trend but RSI is overbought"))
    if (
        trend.direction == TrendDirection.BEARISH
        and oscillator.rsi_state == OscillatorState.OVERSOLD
    ):
        conflicts.append(Conflict("Bearish trend but RSI is oversold"))

    if trend.direction == TrendDirection.BULLISH and volume.price_above_vwap is False:
        conflicts.append(Conflict("Bullish trend but price is below VWAP"))
    if trend.direction == TrendDirection.BEARISH and volume.price_above_vwap is True:
        conflicts.append(Conflict("Bearish trend but price is above VWAP"))

    return ConflictReport(conflicts=conflicts)

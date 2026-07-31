"""Shared value objects for the Technical Analysis Engine (docs/42).

Every analyzer consumes/produces these plain, immutable dataclasses -
deterministic data in, structured evidence out. No analyzer touches the
database or calls anything probabilistic (ADR-005, ADR-006, ADR-031).
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.models.enums import Timeframe


class TrendDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"


class TrendStrengthLevel(StrEnum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class MultiTimeframeVerdict(StrEnum):
    BULLISH_ALIGNMENT = "bullish_alignment"
    BEARISH_ALIGNMENT = "bearish_alignment"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class MovingAverageEvidence:
    """docs/08 §5 Trend indicators, interpreted as alignment facts."""

    price_above_ema20: bool | None
    price_above_ema50: bool | None
    price_above_ema100: bool | None
    price_above_ema200: bool | None
    price_above_sma200: bool | None
    bullish_alignment: bool
    bearish_alignment: bool
    alignment_score: float  # 0.0-1.0: fraction of the 4 EMA pairs in bullish order


@dataclass(frozen=True, slots=True)
class TrendEvidence:
    """docs/08 §7 Trend Detection - the final trend/strength verdict."""

    direction: TrendDirection
    strength: TrendStrengthLevel
    adx: float | None
    di_plus: float | None
    di_minus: float | None
    moving_average: MovingAverageEvidence


@dataclass(frozen=True, slots=True)
class MomentumEvidence:
    """docs/08 §5 Momentum: MACD + raw Momentum indicator."""

    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    macd_bullish: bool | None
    momentum: float | None
    momentum_positive: bool | None


class OscillatorState(StrEnum):
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class OscillatorEvidence:
    """docs/08 §5 Momentum oscillators: RSI, Stochastic RSI, CCI."""

    rsi: float | None
    rsi_state: OscillatorState
    stoch_rsi: float | None
    stoch_rsi_state: OscillatorState
    cci: float | None
    cci_state: OscillatorState


class VolatilityState(StrEnum):
    SQUEEZE = "squeeze"
    NEAR_UPPER_BAND = "near_upper_band"
    NEAR_LOWER_BAND = "near_lower_band"
    STABLE = "stable"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class VolatilityEvidence:
    """docs/08 §5 Volatility: ATR, Bollinger Bands, Standard Deviation."""

    atr: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    stddev: float | None
    state: VolatilityState


class VolumeState(StrEnum):
    ABOVE_AVERAGE = "above_average"
    BELOW_AVERAGE = "below_average"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class VolumeEvidence:
    """docs/08 §5 Volume: VWAP, OBV, Relative Volume."""

    price_above_vwap: bool | None
    obv: float | None
    relative_volume: float | None
    relative_volume_state: VolumeState


@dataclass(frozen=True, slots=True)
class SupportResistanceLevel:
    """A single support/resistance candidate, with explainability metadata
    (refinement: strength + source), not just a bare price."""

    price: Decimal
    source: str  # e.g. "swing_low", "daily_high", "round_number"
    strength: (
        str  # "weak" | "moderate" | "strong" - how many independent sources agree at this level
    )


@dataclass(frozen=True, slots=True)
class SupportResistanceEvidence:
    nearest_support: SupportResistanceLevel | None
    nearest_resistance: SupportResistanceLevel | None
    support_levels: list[SupportResistanceLevel] = field(default_factory=list)
    resistance_levels: list[SupportResistanceLevel] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Conflict:
    description: str


@dataclass(frozen=True, slots=True)
class ConflictReport:
    conflicts: list[Conflict]

    @property
    def is_mixed(self) -> bool:
        return len(self.conflicts) >= 2


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Refinement: explainable score components, not just the final total."""

    trend: float
    momentum: float
    oscillator: float
    volume: float
    volatility: float
    support_resistance: float
    penalties: float  # <= 0

    @property
    def total(self) -> float:
        raw = (
            self.trend
            + self.momentum
            + self.oscillator
            + self.volume
            + self.volatility
            + self.support_resistance
            + self.penalties
        )
        return max(0.0, min(100.0, raw))


@dataclass(frozen=True, slots=True)
class TimeframeTrendSummary:
    timeframe: Timeframe
    direction: TrendDirection
    strength: TrendStrengthLevel


@dataclass(frozen=True, slots=True)
class MultiTimeframeResult:
    symbol: str
    verdict: MultiTimeframeVerdict
    timeframes: list[TimeframeTrendSummary]


@dataclass(frozen=True, slots=True)
class TechnicalAnalysisResult:
    """The engine's final aggregated output (docs/08 §11, docs/42)."""

    symbol: str
    timeframe: Timeframe
    trend: TrendDirection
    strength: TrendStrengthLevel
    technical_score: float
    score_breakdown: ScoreBreakdown
    support: SupportResistanceLevel | None
    resistance: SupportResistanceLevel | None
    support_levels: list[SupportResistanceLevel]
    resistance_levels: list[SupportResistanceLevel]
    indicators: dict[str, float]
    warnings: list[str]
    calculated_at: datetime

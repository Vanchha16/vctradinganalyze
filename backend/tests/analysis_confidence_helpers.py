"""Minimal-but-valid factory functions for building
`TechnicalAnalysisResult`/`SMCAnalysisResult`/`MarketRegimeResult`
fixtures directly (not via their engines) - Confidence Engine unit tests
only care about a handful of fields on each (score, trend/structure
direction, warnings, calculated_at), but every dataclass field must be
populated to construct one."""

from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import Timeframe
from app.services.market_regime.types import (
    AccumulationDistributionEvidence,
    BreakoutEvidence,
    ExpansionEvidence,
    ExpansionState,
    MarketRegimeResult,
    MarketRegimeState,
    PullbackReversalEvidence,
    RangeEvidence,
    RegimeConfidenceBreakdown,
    RegimeConflictReport,
    TransitionEvidence,
    TrendRegimeEvidence,
    VolatilityRegimeEvidence,
    VolatilityRegimeState,
)
from app.services.smc.types import (
    BOSEvidence,
    ConfluenceEvidence,
    Direction,
    MarketStructureEvidence,
    MarketStructureState,
    PremiumDiscountEvidence,
    PremiumDiscountPosition,
    SMCAnalysisResult,
    SMCScoreBreakdown,
)
from app.services.technical_analysis.types import (
    MomentumEvidence,
    MovingAverageEvidence,
    OscillatorEvidence,
    OscillatorState,
    ScoreBreakdown,
    SupportResistanceLevel,
    TechnicalAnalysisResult,
    TrendDirection,
    TrendEvidence,
    TrendStrengthLevel,
    VolatilityEvidence,
    VolatilityState,
    VolumeEvidence,
    VolumeState,
)

_CALCULATED_AT = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


def make_technical_result(
    *,
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    trend: TrendDirection = TrendDirection.BULLISH,
    technical_score: float = 70.0,
    warnings: list[str] | None = None,
    calculated_at: datetime = _CALCULATED_AT,
    has_support_resistance: bool = True,
) -> TechnicalAnalysisResult:
    moving_average = MovingAverageEvidence(
        price_above_ema20=True,
        price_above_ema50=True,
        price_above_ema100=True,
        price_above_ema200=True,
        price_above_sma200=True,
        bullish_alignment=True,
        bearish_alignment=False,
        alignment_score=1.0,
    )
    return TechnicalAnalysisResult(
        symbol=symbol,
        timeframe=timeframe,
        trend=trend,
        strength=TrendStrengthLevel.STRONG,
        technical_score=technical_score,
        score_breakdown=ScoreBreakdown(
            trend=technical_score * 0.4,
            momentum=technical_score * 0.2,
            oscillator=technical_score * 0.15,
            volume=technical_score * 0.15,
            volatility=technical_score * 0.1,
            support_resistance=0.0,
            penalties=0.0,
        ),
        support=(
            SupportResistanceLevel(price=Decimal("1.1000"), source="swing_low", strength="moderate")
            if has_support_resistance
            else None
        ),
        resistance=(
            SupportResistanceLevel(
                price=Decimal("1.1100"), source="swing_high", strength="moderate"
            )
            if has_support_resistance
            else None
        ),
        support_levels=[],
        resistance_levels=[],
        indicators={},
        warnings=warnings or [],
        calculated_at=calculated_at,
        trend_evidence=TrendEvidence(
            direction=trend,
            strength=TrendStrengthLevel.STRONG,
            adx=30.0,
            di_plus=25.0,
            di_minus=10.0,
            moving_average=moving_average,
        ),
        momentum=MomentumEvidence(
            macd=0.001,
            macd_signal=0.0005,
            macd_histogram=0.0005,
            macd_bullish=True,
            momentum=1.0,
            momentum_positive=True,
        ),
        oscillator=OscillatorEvidence(
            rsi=58.0,
            rsi_state=OscillatorState.HEALTHY,
            stoch_rsi=60.0,
            stoch_rsi_state=OscillatorState.HEALTHY,
            cci=50.0,
            cci_state=OscillatorState.HEALTHY,
        ),
        volatility=VolatilityEvidence(
            atr=0.001,
            bollinger_upper=1.11,
            bollinger_lower=1.09,
            stddev=0.001,
            state=VolatilityState.STABLE,
        ),
        volume=VolumeEvidence(
            price_above_vwap=True,
            obv=1000.0,
            relative_volume=1.1,
            relative_volume_state=VolumeState.ABOVE_AVERAGE,
        ),
    )


def make_smc_result(
    *,
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    structure_state: MarketStructureState = MarketStructureState.BULLISH,
    smc_score: float = 60.0,
    warnings: list[str] | None = None,
    calculated_at: datetime = _CALCULATED_AT,
    has_structural_evidence: bool = True,
) -> SMCAnalysisResult:
    return SMCAnalysisResult(
        symbol=symbol,
        timeframe=timeframe,
        market_structure=MarketStructureEvidence(state=structure_state, classifications=[]),
        bos=(
            [
                BOSEvidence(
                    direction=Direction.BULLISH,
                    break_price=Decimal("1.1050"),
                    break_time=calculated_at,
                    strength=1.0,
                    confirmed=True,
                )
            ]
            if has_structural_evidence
            else []
        ),
        choch=[],
        order_blocks=[],
        fair_value_gaps=[],
        liquidity_zones=[],
        liquidity_sweeps=[],
        premium_discount=PremiumDiscountEvidence(
            position=PremiumDiscountPosition.EQUILIBRIUM,
            distance=0.0,
            range_high=Decimal("1.1100"),
            range_low=Decimal("1.0900"),
            equilibrium=Decimal("1.1000"),
        ),
        confluence=ConfluenceEvidence(factors=[], confluence_score=0.0),
        score_breakdown=SMCScoreBreakdown(
            market_structure=smc_score * 0.5,
            order_blocks=smc_score * 0.2,
            fair_value_gaps=smc_score * 0.1,
            liquidity=smc_score * 0.1,
            premium_discount=smc_score * 0.1,
            confluence=0.0,
            penalties=0.0,
        ),
        warnings=warnings or [],
        calculated_at=calculated_at,
    )


def make_regime_result(
    *,
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    regime: MarketRegimeState = MarketRegimeState.TRENDING_BULLISH,
    direction: TrendDirection = TrendDirection.BULLISH,
    aligned: bool = True,
    confidence: float = 65.0,
    warnings: list[str] | None = None,
    calculated_at: datetime = _CALCULATED_AT,
) -> MarketRegimeResult:
    return MarketRegimeResult(
        symbol=symbol,
        timeframe=timeframe,
        regime=regime,
        confidence_breakdown=RegimeConfidenceBreakdown(
            trend_clarity=confidence * 0.4,
            volatility_clarity=confidence * 0.2,
            structural_confirmation=confidence * 0.4,
            stability_penalty=0.0,
            conflict_penalty=0.0,
        ),
        trend_regime=TrendRegimeEvidence(
            direction=direction,
            strength=TrendStrengthLevel.STRONG,
            structure_state=(
                MarketStructureState.BULLISH
                if direction == TrendDirection.BULLISH
                else MarketStructureState.BEARISH
            ),
            aligned=aligned,
        ),
        volatility=VolatilityRegimeEvidence(
            state=VolatilityRegimeState.NORMAL, recent_atr_average=1.0, baseline_atr_average=1.0
        ),
        range=RangeEvidence(is_ranging=False, range_width=None, range_strength=None),
        expansion=ExpansionEvidence(state=ExpansionState.STABLE, ratio=1.0),
        transition=TransitionEvidence(shifting=False, from_hint=None, to_hint=None, confidence=0.0),
        accumulation_distribution=AccumulationDistributionEvidence(
            accumulation_score=0.0, distribution_score=0.0
        ),
        breakout=BreakoutEvidence(detected=False, direction=None, volume_confirmed=False),
        pullback_reversal=PullbackReversalEvidence(
            pullback_depth=None,
            retracement_ratio=None,
            reversal_direction=None,
            reversal_confidence=None,
            exhaustion_warning=None,
        ),
        conflicts=RegimeConflictReport(conflicts=[]),
        candidates=[],
        warnings=warnings or [],
        calculated_at=calculated_at,
    )

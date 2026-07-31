from collections.abc import Sequence

from app.exceptions import ResourceNotFoundException
from app.indicators.types import OHLCVSeries
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.models.price_candle import PriceCandle
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.technical_analysis import (
    conflict_analyzer,
    momentum_analyzer,
    multi_timeframe_analyzer,
    oscillator_analyzer,
    scoring_engine,
    support_resistance_analyzer,
    trend_analyzer,
    volatility_analyzer,
    volume_analyzer,
)
from app.services.technical_analysis.indicator_snapshot import compute_indicator_snapshot
from app.services.technical_analysis.types import (
    MultiTimeframeResult,
    MultiTimeframeVerdict,
    TechnicalAnalysisResult,
    TimeframeTrendSummary,
)

_DEFAULT_LOOKBACK = 500
_MULTI_TIMEFRAME_ORDER = (Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15)
_DAILY_LOOKBACK_FOR_SUPPORT_RESISTANCE = 40  # covers a monthly (30-day) window plus buffer


class TechnicalAnalysisEngine:
    """Deterministic, stateless aggregator (ADR-027, ADR-031): fetch
    candles -> compute indicators fresh -> run analyzers -> assemble one
    `TechnicalAnalysisResult`. No AI, no probabilistic reasoning, no
    persistence - this produces evidence for future consumers (the
    Signal Engine, the AI Orchestrator), it does not decide anything
    itself.
    """

    def __init__(
        self, price_candle_repository: PriceCandleRepository, *, lookback: int = _DEFAULT_LOOKBACK
    ) -> None:
        self._price_candle_repository = price_candle_repository
        self._lookback = lookback

    def analyze(self, asset: Asset, timeframe: Timeframe) -> TechnicalAnalysisResult:
        candles = self._price_candle_repository.list_recent(
            asset.id, timeframe, limit=self._lookback
        )
        if not candles:
            raise ResourceNotFoundException(
                f"No {timeframe.value} candles available for {asset.symbol}"
            )

        series = self._build_series(candles)
        indicators, warnings = compute_indicator_snapshot(series)
        current_price = candles[-1].close
        current_price_float = float(current_price)

        trend = trend_analyzer.analyze(indicators, current_price_float)
        momentum = momentum_analyzer.analyze(indicators)
        oscillator = oscillator_analyzer.analyze(indicators)
        volatility = volatility_analyzer.analyze(indicators, current_price_float)
        volume = volume_analyzer.analyze(indicators, current_price_float)

        daily_candles = (
            candles
            if timeframe == Timeframe.D1
            else self._price_candle_repository.list_recent(
                asset.id, Timeframe.D1, limit=_DAILY_LOOKBACK_FOR_SUPPORT_RESISTANCE
            )
        )
        support_resistance = support_resistance_analyzer.analyze(
            candles, daily_candles, current_price
        )

        conflicts = conflict_analyzer.analyze(trend, momentum, oscillator, volume)
        breakdown = scoring_engine.score(
            trend, momentum, oscillator, volume, volatility, support_resistance, conflicts
        )

        return TechnicalAnalysisResult(
            symbol=asset.symbol,
            timeframe=timeframe,
            trend=trend.direction,
            strength=trend.strength,
            technical_score=breakdown.total,
            score_breakdown=breakdown,
            support=support_resistance.nearest_support,
            resistance=support_resistance.nearest_resistance,
            support_levels=support_resistance.support_levels,
            resistance_levels=support_resistance.resistance_levels,
            indicators={name: output.value for name, output in indicators.items()},
            warnings=[*warnings, *[c.description for c in conflicts.conflicts]],
            calculated_at=candles[-1].timestamp,
            trend_evidence=trend,
            momentum=momentum,
            oscillator=oscillator,
            volatility=volatility,
            volume=volume,
        )

    def analyze_multi_timeframe(self, asset: Asset) -> MultiTimeframeResult:
        summaries: list[TimeframeTrendSummary] = []

        for timeframe in _MULTI_TIMEFRAME_ORDER:
            candles = self._price_candle_repository.list_recent(
                asset.id, timeframe, limit=self._lookback
            )
            if not candles:
                continue

            series = self._build_series(candles)
            indicators, _warnings = compute_indicator_snapshot(series)
            trend = trend_analyzer.analyze(indicators, float(candles[-1].close))
            summaries.append(
                TimeframeTrendSummary(
                    timeframe=timeframe, direction=trend.direction, strength=trend.strength
                )
            )

        verdict = (
            multi_timeframe_analyzer.combine(summaries)
            if summaries
            else MultiTimeframeVerdict.MIXED
        )
        return MultiTimeframeResult(symbol=asset.symbol, verdict=verdict, timeframes=summaries)

    @staticmethod
    def _build_series(candles: Sequence[PriceCandle]) -> OHLCVSeries:
        return OHLCVSeries(
            opens=[float(c.open) for c in candles],
            highs=[float(c.high) for c in candles],
            lows=[float(c.low) for c in candles],
            closes=[float(c.close) for c in candles],
            volumes=[float(c.volume) if c.volume is not None else None for c in candles],
        )

"""Top-level Market Regime Engine orchestrator (docs/44). Stateless
(ADR-038) - classifies market conditions from Technical Analysis's and
SMC's already-computed evidence rather than re-deriving it, computing
only the small amount of genuinely new data neither upstream engine
exposes (an ATR series for volatility/expansion regime detection).

Both upstream engines are called exactly once per (asset, timeframe)
within a single `analyze()` execution, and their results are passed by
parameter to every regime analyzer - never re-invoked per analyzer
(Phase 4C refinement: cache upstream results within one execution).

Unlike Technical Analysis's/SMC's multi-timeframe methods (which only
need a cheap per-timeframe trend/structure summary), a full regime
classification needs the complete evidence set per timeframe - so
`analyze_multi_timeframe()` here calls the full `analyze()` per
timeframe rather than a lighter-weight subset (docs/44 §11).
"""

from app.exceptions import ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_regime import (
    accumulation_distribution_analyzer,
    breakout_analyzer,
    confidence_engine,
    conflict_analyzer,
    expansion_analyzer,
    multi_timeframe_analyzer,
    pullback_reversal_analyzer,
    range_analyzer,
    regime_classifier,
    transition_analyzer,
    trend_regime_analyzer,
    volatility_regime_analyzer,
)
from app.services.market_regime.types import (
    MarketRegimeMultiTimeframeResult,
    MarketRegimeResult,
    MarketRegimeVerdict,
    TimeframeRegimeSummary,
)
from app.services.smc_engine import SMCEngine
from app.services.technical_analysis_engine import TechnicalAnalysisEngine

_DEFAULT_LOOKBACK = 500
_MULTI_TIMEFRAME_ORDER = (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15)


class MarketRegimeEngine:
    """Deterministic classifier (ADR-031, ADR-038): no AI, no
    probabilistic reasoning, no trading recommendations - classifies
    market conditions only, reusing Technical Analysis's and SMC's
    evidence rather than duplicating their calculations.
    """

    def __init__(
        self,
        price_candle_repository: PriceCandleRepository,
        technical_analysis_engine: TechnicalAnalysisEngine,
        smc_engine: SMCEngine,
        *,
        lookback: int = _DEFAULT_LOOKBACK,
    ) -> None:
        self._price_candle_repository = price_candle_repository
        self._technical_analysis_engine = technical_analysis_engine
        self._smc_engine = smc_engine
        self._lookback = lookback

    def analyze(self, asset: Asset, timeframe: Timeframe) -> MarketRegimeResult:
        candles = self._price_candle_repository.list_recent(
            asset.id, timeframe, limit=self._lookback
        )
        if not candles:
            raise ResourceNotFoundException(
                f"No {timeframe.value} candles available for {asset.symbol}"
            )

        # Cache: each upstream engine is called exactly once for this execution.
        technical_analysis = self._technical_analysis_engine.analyze(asset, timeframe)
        smc = self._smc_engine.analyze(asset, timeframe)

        current_price = candles[-1].close

        trend_regime = trend_regime_analyzer.analyze(
            technical_analysis.trend_evidence, smc.market_structure
        )
        volatility = volatility_regime_analyzer.analyze(candles)
        expansion = expansion_analyzer.analyze(volatility)
        range_evidence = range_analyzer.analyze(
            technical_analysis.trend_evidence,
            technical_analysis.support,
            technical_analysis.resistance,
            current_price,
        )
        transition = transition_analyzer.analyze(candles, expansion)
        accumulation_distribution = accumulation_distribution_analyzer.analyze(
            candles, range_evidence, smc.order_blocks, smc.liquidity_sweeps
        )
        breakout = breakout_analyzer.analyze(candles, smc.bos)
        pullback_reversal = pullback_reversal_analyzer.analyze(
            technical_analysis.trend,
            smc.market_structure.classifications,
            current_price,
            smc.choch,
        )

        conflicts = conflict_analyzer.analyze(
            trend_regime, range_evidence, accumulation_distribution
        )

        candidates = regime_classifier.build_candidates(
            trend_regime,
            volatility,
            range_evidence,
            accumulation_distribution,
            breakout,
            pullback_reversal,
        )
        outcome = regime_classifier.classify(candidates)
        confidence_breakdown = confidence_engine.score(trend_regime, volatility, outcome, conflicts)

        warnings = [
            *outcome.warnings,
            *(
                [pullback_reversal.exhaustion_warning]
                if pullback_reversal.exhaustion_warning
                else []
            ),
            *[c.description for c in conflicts.conflicts],
        ]

        return MarketRegimeResult(
            symbol=asset.symbol,
            timeframe=timeframe,
            regime=outcome.regime,
            confidence_breakdown=confidence_breakdown,
            trend_regime=trend_regime,
            volatility=volatility,
            range=range_evidence,
            expansion=expansion,
            transition=transition,
            accumulation_distribution=accumulation_distribution,
            breakout=breakout,
            pullback_reversal=pullback_reversal,
            conflicts=conflicts,
            candidates=outcome.candidates,
            warnings=warnings,
            calculated_at=candles[-1].timestamp,
        )

    def analyze_multi_timeframe(self, asset: Asset) -> MarketRegimeMultiTimeframeResult:
        summaries: list[TimeframeRegimeSummary] = []

        for timeframe in _MULTI_TIMEFRAME_ORDER:
            try:
                result = self.analyze(asset, timeframe)
            except ResourceNotFoundException:
                continue
            summaries.append(TimeframeRegimeSummary(timeframe=timeframe, regime=result.regime))

        verdict = (
            multi_timeframe_analyzer.combine(summaries) if summaries else MarketRegimeVerdict.MIXED
        )
        return MarketRegimeMultiTimeframeResult(
            symbol=asset.symbol, verdict=verdict, timeframes=summaries
        )

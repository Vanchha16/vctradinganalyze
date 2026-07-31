"""Top-level Confidence Engine orchestrator (docs/15, docs/45). Named
`AnalysisConfidenceEngine` - not bare `ConfidenceEngine` - to avoid
confusion with `app/services/market_regime/confidence_engine.py`'s
`RegimeConfidenceEngine`, which scores regime-classification reliability
only, not overall cross-engine analysis reliability (ADR-048).

Fully stateless (ADR-045, mirrors ADR-027/038): no new table, recomputes
from Technical Analysis, SMC, and Market Regime on every call. Evaluates
the QUALITY, COMPLETENESS, and CONSISTENCY of existing evidence - it
never predicts whether a trade will win and never produces a BUY/SELL/
WAIT recommendation (ADR-031, ADR-043, extended here).

Technical Analysis and SMC are each computed at most once per execution
and passed into `MarketRegimeEngine.analyze()` (ADR-049) rather than
letting Regime recompute them itself - avoids the double-computation
that a naive three-independent-calls design would cause.

Any upstream engine that raises `ResourceNotFoundException` degrades
gracefully: its evidence is treated as unavailable (`None`), recorded in
`missing_data`, and confidence is still computed from whatever evidence
remains - never a hard failure for one engine's missing data.
"""

from datetime import UTC, datetime

from app.exceptions import ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.services.analysis_confidence import (
    alignment_analyzer,
    confidence_aggregator,
    conflict_analyzer,
    data_quality_analyzer,
    freshness_analyzer,
    regime_confidence_analyzer,
    smc_confidence_analyzer,
    summary_builder,
    technical_confidence_analyzer,
)
from app.services.analysis_confidence.confidence_aggregator import WeightedComponent
from app.services.analysis_confidence.types import (
    ConfidenceMultiTimeframeResult,
    ConfidenceMultiTimeframeVerdict,
    ConfidenceResult,
    TimeframeConfidenceSummary,
)
from app.services.market_regime.types import MarketRegimeResult
from app.services.market_regime_engine import MarketRegimeEngine
from app.services.smc.types import SMCAnalysisResult
from app.services.smc_engine import SMCEngine
from app.services.technical_analysis.types import TechnicalAnalysisResult
from app.services.technical_analysis_engine import TechnicalAnalysisEngine

_MULTI_TIMEFRAME_ORDER = (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15)

#: docs/45 §6 - a multi-timeframe verdict is ALIGNED only when every
#: available timeframe's confidence is at least MODERATE-and-above in
#: practice (HIGH/VERY_HIGH); anything else is reported as MIXED.
_ALIGNED_LEVELS = {"high", "very_high"}


class AnalysisConfidenceEngine:
    def __init__(
        self,
        technical_analysis_engine: TechnicalAnalysisEngine,
        smc_engine: SMCEngine,
        market_regime_engine: MarketRegimeEngine,
    ) -> None:
        self._technical_analysis_engine = technical_analysis_engine
        self._smc_engine = smc_engine
        self._market_regime_engine = market_regime_engine

    def analyze(self, asset: Asset, timeframe: Timeframe) -> ConfidenceResult:
        missing_data: list[str] = []

        technical: TechnicalAnalysisResult | None
        try:
            technical = self._technical_analysis_engine.analyze(asset, timeframe)
        except ResourceNotFoundException:
            missing_data.append("technical_analysis_unavailable")
            technical = None

        smc: SMCAnalysisResult | None
        try:
            smc = self._smc_engine.analyze(asset, timeframe)
        except ResourceNotFoundException:
            missing_data.append("smc_unavailable")
            smc = None

        market_regime: MarketRegimeResult | None
        try:
            market_regime = self._market_regime_engine.analyze(
                asset, timeframe, technical_analysis=technical, smc=smc
            )
        except ResourceNotFoundException:
            missing_data.append("market_regime_unavailable")
            market_regime = None

        technical_score, technical_direction = technical_confidence_analyzer.analyze(technical)
        smc_score, smc_direction = smc_confidence_analyzer.analyze(smc)
        regime_score, regime_direction = regime_confidence_analyzer.analyze(market_regime)

        alignment = alignment_analyzer.analyze(technical_direction, smc_direction, regime_direction)
        conflicts = conflict_analyzer.analyze(technical, smc, market_regime, alignment)
        conflict_penalty = conflict_analyzer.penalty_for(conflicts)
        conflict_severity = conflict_analyzer.overall_severity(conflicts)

        data_quality = data_quality_analyzer.analyze(technical, smc, market_regime)
        missing_data = [*missing_data, *data_quality.missing_data]

        now = datetime.now(UTC)
        freshness = freshness_analyzer.analyze(technical, smc, market_regime, timeframe, now)

        breakdown = confidence_aggregator.combine(
            [
                WeightedComponent("technical_alignment", technical_score),
                WeightedComponent("smc_alignment", smc_score),
                WeightedComponent("regime_confirmation", regime_score),
                WeightedComponent("cross_engine_agreement", alignment.agreement_score),
                WeightedComponent("data_completeness", data_quality.completeness_score),
                WeightedComponent("freshness", freshness.freshness_score),
            ],
            conflict_penalty,
        )
        confidence_level = confidence_aggregator.level_for(breakdown.total)

        warnings = [
            *(technical.warnings if technical is not None else []),
            *(smc.warnings if smc is not None else []),
            *(market_regime.warnings if market_regime is not None else []),
        ]
        if freshness.is_stale:
            warnings.append("One or more upstream analyses are stale for this timeframe.")

        summary = summary_builder.build(
            breakdown.total, confidence_level, alignment, conflicts, missing_data
        )

        return ConfidenceResult(
            symbol=asset.symbol,
            timeframe=timeframe,
            overall_confidence=breakdown.total,
            confidence_level=confidence_level,
            summary=summary,
            technical=technical,
            smc=smc,
            market_regime=market_regime,
            alignment=alignment,
            conflicts=conflicts,
            conflict_severity=conflict_severity,
            missing_data=missing_data,
            warnings=warnings,
            breakdown=breakdown,
            calculated_at=now,
        )

    def analyze_multi_timeframe(self, asset: Asset) -> ConfidenceMultiTimeframeResult:
        summaries: list[TimeframeConfidenceSummary] = []

        for timeframe in _MULTI_TIMEFRAME_ORDER:
            result = self.analyze(asset, timeframe)
            summaries.append(
                TimeframeConfidenceSummary(
                    timeframe=timeframe,
                    overall_confidence=result.overall_confidence,
                    confidence_level=result.confidence_level,
                )
            )

        verdict = (
            ConfidenceMultiTimeframeVerdict.ALIGNED
            if summaries and all(s.confidence_level.value in _ALIGNED_LEVELS for s in summaries)
            else ConfidenceMultiTimeframeVerdict.MIXED
        )
        return ConfidenceMultiTimeframeResult(
            symbol=asset.symbol, verdict=verdict, timeframes=summaries
        )

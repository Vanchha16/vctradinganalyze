"""Top-level SMC Engine orchestrator (docs/43). Runs every analyzer over
a bounded recent candle window, persists detected/updated `SMCEvent`
rows (de-duplicated against existing rows for the same zone rather than
inserted again - ADR-033), records a processing checkpoint, and returns
the aggregated evidence.

Bounding each pass to `_DEFAULT_LOOKBACK` candles (rather than the full
asset history) is what keeps this fast as history grows - a full
delta-only scan that skips re-examining already-persisted zones is a
documented future optimization (BACKLOG), not required to meet docs/43
§19's performance targets at this scale.
"""

import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

from app.exceptions import ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import SMCEventStatus, SMCEventType, Timeframe
from app.models.smc_event import SMCEvent
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.smc import (
    bos_analyzer,
    breaker_block_analyzer,
    choch_analyzer,
    conflict_analyzer,
    confluence_analyzer,
    fair_value_gap_analyzer,
    liquidity_analyzer,
    market_structure_analyzer,
    mitigation_analyzer,
    multi_timeframe_analyzer,
    order_block_analyzer,
    premium_discount_analyzer,
    scoring_engine,
)
from app.services.smc.types import (
    Direction,
    FairValueGapEvidence,
    OrderBlockEvidence,
    SMCAnalysisResult,
    SMCConflictReport,
    SMCMultiTimeframeResult,
    SMCVerdict,
    TimeframeMarketStructureSummary,
)

SMC_ENGINE_VERSION = "1.0.0"

_DEFAULT_LOOKBACK = 500
_MIN_CANDLES = 20
_MULTI_TIMEFRAME_ORDER = (Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15)

#: Resolved zones (MITIGATED/INVALIDATED) older than this are archived
#: (ADR-037) - they remain queryable (never deleted) but drop out of the
#: default "active-ish" view returned to API consumers.
_ARCHIVE_AFTER = timedelta(days=30)

_ORDER_BLOCK_EVENT_TYPE = {
    Direction.BULLISH: SMCEventType.ORDER_BLOCK_BULLISH,
    Direction.BEARISH: SMCEventType.ORDER_BLOCK_BEARISH,
}
_FVG_EVENT_TYPE = {
    Direction.BULLISH: SMCEventType.FAIR_VALUE_GAP_BULLISH,
    Direction.BEARISH: SMCEventType.FAIR_VALUE_GAP_BEARISH,
}


class SMCEngine:
    """Deterministic aggregator (ADR-031, ADR-036): no AI, no
    probabilistic reasoning, no trading recommendations - only
    structured evidence. Persists to `smc_events` (ADR-032), unlike the
    stateless Technical Analysis Engine (ADR-027), because SMC concepts
    have genuine lifecycle state.
    """

    def __init__(
        self,
        price_candle_repository: PriceCandleRepository,
        smc_event_repository: SMCEventRepository,
        smc_processing_state_repository: SMCProcessingStateRepository,
        *,
        lookback: int = _DEFAULT_LOOKBACK,
    ) -> None:
        self._price_candle_repository = price_candle_repository
        self._smc_event_repository = smc_event_repository
        self._smc_processing_state_repository = smc_processing_state_repository
        self._lookback = lookback

    def analyze(self, asset: Asset, timeframe: Timeframe) -> SMCAnalysisResult:
        candles = self._price_candle_repository.list_recent(
            asset.id, timeframe, limit=self._lookback
        )
        if not candles:
            raise ResourceNotFoundException(
                f"No {timeframe.value} candles available for {asset.symbol}"
            )

        warnings: list[str] = []
        if len(candles) < _MIN_CANDLES:
            warnings.append(
                f"Only {len(candles)} candles available (recommended minimum {_MIN_CANDLES}); "
                "detection quality may be reduced."
            )

        market_structure = market_structure_analyzer.analyze(candles)
        bos_events = bos_analyzer.analyze(candles)
        choch_events = choch_analyzer.analyze(candles)

        order_blocks = order_block_analyzer.analyze(candles)
        order_blocks = mitigation_analyzer.analyze(candles, order_blocks)
        order_blocks = breaker_block_analyzer.analyze(candles, order_blocks)

        fair_value_gaps = fair_value_gap_analyzer.analyze(candles)
        liquidity_zones, liquidity_sweeps = liquidity_analyzer.analyze(candles)
        premium_discount = premium_discount_analyzer.analyze(candles, candles[-1].close)

        now = candles[-1].timestamp
        _archive_stale_order_blocks(order_blocks, now)
        fair_value_gaps = _archive_stale_fair_value_gaps(fair_value_gaps, now)

        confluence = confluence_analyzer.analyze(
            market_structure, bos_events, order_blocks, premium_discount, liquidity_sweeps
        )
        score_breakdown = scoring_engine.score(
            market_structure,
            order_blocks,
            fair_value_gaps,
            liquidity_zones,
            len(liquidity_sweeps),
            premium_discount,
            confluence,
            len(warnings),
        )

        self._persist_order_blocks(asset.id, timeframe, order_blocks)
        self._persist_fair_value_gaps(asset.id, timeframe, fair_value_gaps)
        self._smc_processing_state_repository.upsert(
            asset.id,
            timeframe,
            last_processed_timestamp=candles[-1].timestamp,
            engine_version=SMC_ENGINE_VERSION,
        )
        self._smc_event_repository.commit()

        return SMCAnalysisResult(
            symbol=asset.symbol,
            timeframe=timeframe,
            market_structure=market_structure,
            bos=bos_events,
            choch=choch_events,
            order_blocks=order_blocks,
            fair_value_gaps=fair_value_gaps,
            liquidity_zones=liquidity_zones,
            liquidity_sweeps=liquidity_sweeps,
            premium_discount=premium_discount,
            confluence=confluence,
            score_breakdown=score_breakdown,
            warnings=warnings,
            calculated_at=candles[-1].timestamp,
        )

    def analyze_multi_timeframe(self, asset: Asset) -> SMCMultiTimeframeResult:
        summaries: list[TimeframeMarketStructureSummary] = []

        for timeframe in _MULTI_TIMEFRAME_ORDER:
            candles = self._price_candle_repository.list_recent(
                asset.id, timeframe, limit=self._lookback
            )
            if not candles:
                continue
            structure = market_structure_analyzer.analyze(candles)
            summaries.append(
                TimeframeMarketStructureSummary(timeframe=timeframe, state=structure.state)
            )

        verdict = multi_timeframe_analyzer.combine(summaries) if summaries else SMCVerdict.MIXED

        conflict = SMCConflictReport(is_pullback=False, conflicts=[])
        if len(summaries) >= 2:
            conflict = conflict_analyzer.analyze(summaries[0].state, summaries[-1].state)

        return SMCMultiTimeframeResult(
            symbol=asset.symbol, verdict=verdict, timeframes=summaries, conflict=conflict
        )

    def _persist_order_blocks(
        self, asset_id: uuid.UUID, timeframe: Timeframe, order_blocks: Sequence[OrderBlockEvidence]
    ) -> None:
        for ob in order_blocks:
            event_type = _ORDER_BLOCK_EVENT_TYPE[ob.direction]
            existing = self._smc_event_repository.get_by_natural_key(
                asset_id, timeframe, event_type, ob.created_at
            )
            context = {
                "zone_high": str(ob.zone_high),
                "zone_low": str(ob.zone_low),
                "touched": ob.touched,
                "mitigated": ob.mitigated,
                "broken": ob.broken,
                "is_breaker": ob.is_breaker,
                "breaker_confirmed": ob.breaker_confirmed,
                "retest_count": ob.retest_count,
                "strength_score": ob.strength_score,
                "freshness_score": ob.freshness_score,
                "volume_confirmed": ob.volume_confirmed,
            }
            if existing is None:
                event = SMCEvent(
                    asset_id=asset_id,
                    timeframe=timeframe,
                    event_type=event_type,
                    status=ob.status,
                    price=ob.zone_high,
                    strength=Decimal(str(ob.strength_score)),
                    context=context,
                    detected_at=ob.created_at,
                )
                self._smc_event_repository.create(event)
            else:
                existing.status = ob.status
                existing.context = context
                self._smc_event_repository.session.flush()

    def _persist_fair_value_gaps(
        self, asset_id: uuid.UUID, timeframe: Timeframe, gaps: Sequence[FairValueGapEvidence]
    ) -> None:
        for gap in gaps:
            event_type = _FVG_EVENT_TYPE[gap.direction]
            existing = self._smc_event_repository.get_by_natural_key(
                asset_id, timeframe, event_type, gap.created_at
            )
            context = {
                "gap_high": str(gap.gap_high),
                "gap_low": str(gap.gap_low),
                "gap_size": str(gap.gap_size),
                "priority": gap.priority,
            }
            if existing is None:
                event = SMCEvent(
                    asset_id=asset_id,
                    timeframe=timeframe,
                    event_type=event_type,
                    status=gap.status,
                    price=gap.gap_high,
                    strength=None,
                    context=context,
                    detected_at=gap.created_at,
                )
                self._smc_event_repository.create(event)
            else:
                existing.status = gap.status
                existing.context = context
                self._smc_event_repository.session.flush()


def _archive_stale_order_blocks(order_blocks: Sequence[OrderBlockEvidence], now: datetime) -> None:
    for ob in order_blocks:
        if ob.status in (SMCEventStatus.MITIGATED, SMCEventStatus.INVALIDATED) and (
            now - ob.created_at > _ARCHIVE_AFTER
        ):
            ob.status = SMCEventStatus.ARCHIVED


def _archive_stale_fair_value_gaps(
    gaps: Sequence[FairValueGapEvidence], now: datetime
) -> list[FairValueGapEvidence]:
    return [
        (
            replace(gap, status=SMCEventStatus.ARCHIVED)
            if gap.status == SMCEventStatus.MITIGATED and (now - gap.created_at > _ARCHIVE_AFTER)
            else gap
        )
        for gap in gaps
    ]

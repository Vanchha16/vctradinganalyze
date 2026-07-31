"""SMCScoringEngine: produces `SMCScoreBreakdown`, mirroring Technical
Analysis's `ScoreBreakdown` pattern (docs/42, ADR-028) with a component
per concept plus a penalties term - but this `smc_score` measures
institutional-structure evidence strength (freshness, alignment,
confluence), not indicator agreement, so it is never combined with
`technical_score` by either engine (ADR-036).
"""

from collections.abc import Sequence

from app.models.enums import SMCEventStatus
from app.services.smc.types import (
    ConfluenceEvidence,
    FairValueGapEvidence,
    LiquidityZoneEvidence,
    MarketStructureEvidence,
    MarketStructureState,
    OrderBlockEvidence,
    PremiumDiscountEvidence,
    PremiumDiscountPosition,
    SMCScoreBreakdown,
)

_MARKET_STRUCTURE_WEIGHT = 20.0
_ORDER_BLOCK_WEIGHT = 20.0
_FVG_WEIGHT_PER_GAP = 5.0
_FVG_WEIGHT_MAX = 15.0
_LIQUIDITY_ZONE_WEIGHT = 10.0
_LIQUIDITY_SWEEP_WEIGHT = 5.0
_PREMIUM_DISCOUNT_WEIGHT = 10.0
_CONFLUENCE_SCALE = 0.20
_PENALTY_PER_WARNING = 5.0


def _market_structure_score(evidence: MarketStructureEvidence) -> float:
    if evidence.state in (MarketStructureState.BULLISH, MarketStructureState.BEARISH):
        return _MARKET_STRUCTURE_WEIGHT
    if evidence.state == MarketStructureState.TRANSITION:
        return _MARKET_STRUCTURE_WEIGHT * 0.25
    return 0.0


def _order_block_score(order_blocks: Sequence[OrderBlockEvidence]) -> float:
    active = [ob for ob in order_blocks if ob.status == SMCEventStatus.ACTIVE]
    if not active:
        return 0.0
    best_freshness = max(ob.freshness_score for ob in active)
    return _ORDER_BLOCK_WEIGHT * best_freshness


def _fvg_score(gaps: Sequence[FairValueGapEvidence]) -> float:
    open_gaps = [g for g in gaps if g.status == SMCEventStatus.ACTIVE]
    return min(_FVG_WEIGHT_MAX, len(open_gaps) * _FVG_WEIGHT_PER_GAP)


def _liquidity_score(zones: Sequence[LiquidityZoneEvidence], sweep_count: int) -> float:
    score = _LIQUIDITY_ZONE_WEIGHT if zones else 0.0
    score += _LIQUIDITY_SWEEP_WEIGHT if sweep_count else 0.0
    return score


def _premium_discount_score(
    market_structure: MarketStructureEvidence, premium_discount: PremiumDiscountEvidence
) -> float:
    favorable = (
        market_structure.state == MarketStructureState.BULLISH
        and premium_discount.position == PremiumDiscountPosition.DISCOUNT
    ) or (
        market_structure.state == MarketStructureState.BEARISH
        and premium_discount.position == PremiumDiscountPosition.PREMIUM
    )
    return _PREMIUM_DISCOUNT_WEIGHT if favorable else 0.0


def score(
    market_structure: MarketStructureEvidence,
    order_blocks: Sequence[OrderBlockEvidence],
    fair_value_gaps: Sequence[FairValueGapEvidence],
    liquidity_zones: Sequence[LiquidityZoneEvidence],
    liquidity_sweep_count: int,
    premium_discount: PremiumDiscountEvidence,
    confluence: ConfluenceEvidence,
    warning_count: int,
) -> SMCScoreBreakdown:
    return SMCScoreBreakdown(
        market_structure=_market_structure_score(market_structure),
        order_blocks=_order_block_score(order_blocks),
        fair_value_gaps=_fvg_score(fair_value_gaps),
        liquidity=_liquidity_score(liquidity_zones, liquidity_sweep_count),
        premium_discount=_premium_discount_score(market_structure, premium_discount),
        confluence=confluence.confluence_score * _CONFLUENCE_SCALE,
        penalties=warning_count * _PENALTY_PER_WARNING,
    )

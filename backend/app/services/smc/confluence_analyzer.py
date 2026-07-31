"""docs/09 §14 Confluence Detection: checks a small set of independent
factors (structure/BOS alignment, an aligned active order block, a
favorable premium/discount position, a supporting liquidity sweep) and
sums their weights, capped at 100. This becomes one component of the
overall `smc_score` (docs/43 §6), not a second, competing score.
"""

from collections.abc import Sequence

from app.models.enums import SMCEventStatus
from app.services.smc.types import (
    BOSEvidence,
    ConfluenceEvidence,
    Direction,
    LiquiditySweepEvidence,
    MarketStructureEvidence,
    MarketStructureState,
    OrderBlockEvidence,
    PremiumDiscountEvidence,
    PremiumDiscountPosition,
)

_FACTOR_WEIGHT = 25.0


def analyze(
    market_structure: MarketStructureEvidence,
    bos_events: Sequence[BOSEvidence],
    order_blocks: Sequence[OrderBlockEvidence],
    premium_discount: PremiumDiscountEvidence,
    liquidity_sweeps: Sequence[LiquiditySweepEvidence],
) -> ConfluenceEvidence:
    factors: list[str] = []

    structure_direction = (
        Direction.BULLISH
        if market_structure.state == MarketStructureState.BULLISH
        else Direction.BEARISH if market_structure.state == MarketStructureState.BEARISH else None
    )

    if structure_direction is not None and any(
        b.direction == structure_direction for b in bos_events
    ):
        factors.append("structure_confirmed_by_bos")

    if structure_direction is not None and any(
        ob.direction == structure_direction and ob.status == SMCEventStatus.ACTIVE
        for ob in order_blocks
    ):
        factors.append("order_block_alignment")

    favorable_zone = (
        structure_direction == Direction.BULLISH
        and premium_discount.position == PremiumDiscountPosition.DISCOUNT
    ) or (
        structure_direction == Direction.BEARISH
        and premium_discount.position == PremiumDiscountPosition.PREMIUM
    )
    if favorable_zone:
        factors.append("favorable_zone")

    if liquidity_sweeps:
        factors.append("liquidity_sweep_confirmation")

    score = min(100.0, len(factors) * _FACTOR_WEIGHT)
    return ConfluenceEvidence(factors=factors, confluence_score=score)

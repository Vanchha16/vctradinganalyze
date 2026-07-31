from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.services.smc import confluence_analyzer
from app.services.smc.types import (
    BOSEvidence,
    Direction,
    LiquiditySide,
    LiquiditySweepEvidence,
    MarketStructureEvidence,
    MarketStructureState,
    OrderBlockEvidence,
    PremiumDiscountEvidence,
    PremiumDiscountPosition,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _order_block(direction: Direction, status: SMCEventStatus) -> OrderBlockEvidence:
    return OrderBlockEvidence(
        direction=direction,
        zone_high=Decimal("12"),
        zone_low=Decimal("10"),
        created_at=_NOW,
        status=status,
        touched=False,
        mitigated=False,
        broken=False,
        strength_score=0.5,
        freshness_score=1.0,
        volume_confirmed=True,
    )


def test_all_factors_align_for_high_confluence() -> None:
    market_structure = MarketStructureEvidence(
        state=MarketStructureState.BULLISH, classifications=[]
    )
    bos = [
        BOSEvidence(
            direction=Direction.BULLISH,
            break_price=Decimal("12"),
            break_time=_NOW,
            strength=1.0,
            confirmed=True,
        )
    ]
    order_blocks = [_order_block(Direction.BULLISH, SMCEventStatus.ACTIVE)]
    premium_discount = PremiumDiscountEvidence(
        position=PremiumDiscountPosition.DISCOUNT,
        distance=-0.5,
        range_high=Decimal("20"),
        range_low=Decimal("10"),
        equilibrium=Decimal("15"),
    )
    sweeps = [
        LiquiditySweepEvidence(
            side=LiquiditySide.SELL_SIDE, level=Decimal("9"), sweep_time=_NOW, false_breakout=True
        )
    ]

    evidence = confluence_analyzer.analyze(
        market_structure, bos, order_blocks, premium_discount, sweeps
    )

    assert set(evidence.factors) == {
        "structure_confirmed_by_bos",
        "order_block_alignment",
        "favorable_zone",
        "liquidity_sweep_confirmation",
    }
    assert evidence.confluence_score == 100.0


def test_no_factors_yields_zero_confluence() -> None:
    market_structure = MarketStructureEvidence(state=MarketStructureState.RANGE, classifications=[])
    premium_discount = PremiumDiscountEvidence(
        position=PremiumDiscountPosition.EQUILIBRIUM,
        distance=0.0,
        range_high=Decimal("20"),
        range_low=Decimal("10"),
        equilibrium=Decimal("15"),
    )

    evidence = confluence_analyzer.analyze(market_structure, [], [], premium_discount, [])

    assert evidence.factors == []
    assert evidence.confluence_score == 0.0

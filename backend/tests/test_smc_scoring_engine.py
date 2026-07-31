from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.services.smc import scoring_engine
from app.services.smc.types import (
    ConfluenceEvidence,
    Direction,
    FairValueGapEvidence,
    LiquiditySide,
    LiquidityZoneEvidence,
    MarketStructureEvidence,
    MarketStructureState,
    OrderBlockEvidence,
    PremiumDiscountEvidence,
    PremiumDiscountPosition,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_full_alignment_scores_high() -> None:
    market_structure = MarketStructureEvidence(
        state=MarketStructureState.BULLISH, classifications=[]
    )
    order_blocks = [
        OrderBlockEvidence(
            direction=Direction.BULLISH,
            zone_high=Decimal("12"),
            zone_low=Decimal("10"),
            created_at=_NOW,
            status=SMCEventStatus.ACTIVE,
            touched=False,
            mitigated=False,
            broken=False,
            strength_score=0.8,
            freshness_score=1.0,
            volume_confirmed=True,
        )
    ]
    gaps = [
        FairValueGapEvidence(
            direction=Direction.BULLISH,
            gap_high=Decimal("11"),
            gap_low=Decimal("10"),
            created_at=_NOW,
            status=SMCEventStatus.ACTIVE,
            gap_size=Decimal("1"),
            priority="high",
        )
    ]
    zones = [
        LiquidityZoneEvidence(
            side=LiquiditySide.SELL_SIDE,
            level=Decimal("9"),
            touch_count=2,
            status=SMCEventStatus.ACTIVE,
            created_at=_NOW,
        )
    ]
    premium_discount = PremiumDiscountEvidence(
        position=PremiumDiscountPosition.DISCOUNT,
        distance=-0.5,
        range_high=Decimal("20"),
        range_low=Decimal("10"),
        equilibrium=Decimal("15"),
    )
    confluence = ConfluenceEvidence(factors=["a", "b"], confluence_score=100.0)

    breakdown = scoring_engine.score(
        market_structure, order_blocks, gaps, zones, 1, premium_discount, confluence, 0
    )

    assert breakdown.market_structure == 20.0
    assert breakdown.order_blocks == 20.0
    assert breakdown.fair_value_gaps == 5.0
    assert breakdown.liquidity == 15.0
    assert breakdown.premium_discount == 10.0
    assert breakdown.confluence == 20.0
    assert breakdown.penalties == 0.0
    assert breakdown.total == 90.0


def test_no_evidence_scores_zero() -> None:
    market_structure = MarketStructureEvidence(state=MarketStructureState.RANGE, classifications=[])
    premium_discount = PremiumDiscountEvidence(
        position=PremiumDiscountPosition.EQUILIBRIUM,
        distance=0.0,
        range_high=Decimal("20"),
        range_low=Decimal("10"),
        equilibrium=Decimal("15"),
    )
    confluence = ConfluenceEvidence(factors=[], confluence_score=0.0)

    breakdown = scoring_engine.score(
        market_structure, [], [], [], 0, premium_discount, confluence, 2
    )

    assert breakdown.total == 0.0
    assert breakdown.penalties == 10.0


def test_score_never_exceeds_100_or_goes_negative() -> None:
    market_structure = MarketStructureEvidence(
        state=MarketStructureState.BULLISH, classifications=[]
    )
    premium_discount = PremiumDiscountEvidence(
        position=PremiumDiscountPosition.DISCOUNT,
        distance=-1.0,
        range_high=Decimal("20"),
        range_low=Decimal("10"),
        equilibrium=Decimal("15"),
    )
    confluence = ConfluenceEvidence(factors=["a", "b", "c", "d"], confluence_score=100.0)

    breakdown = scoring_engine.score(
        market_structure, [], [], [], 100, premium_discount, confluence, 0
    )

    assert 0.0 <= breakdown.total <= 100.0

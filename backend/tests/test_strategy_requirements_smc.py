from decimal import Decimal

from app.models.enums import SMCEventStatus, Timeframe
from app.services.smc.types import (
    BOSEvidence,
    CHOCHEvidence,
    ConfluenceEvidence,
    Direction,
    FairValueGapEvidence,
    LiquiditySide,
    LiquiditySweepEvidence,
    LiquidityZoneEvidence,
    MarketStructureEvidence,
    MarketStructureState,
    OrderBlockEvidence,
    PremiumDiscountEvidence,
    PremiumDiscountPosition,
    SMCAnalysisResult,
    SMCScoreBreakdown,
)
from app.services.strategy.requirements.smc import check
from tests.analysis_confidence_helpers import _CALCULATED_AT
from tests.strategy_helpers import make_evidence_bundle


def _full_smc_result() -> SMCAnalysisResult:
    return SMCAnalysisResult(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        market_structure=MarketStructureEvidence(
            state=MarketStructureState.BULLISH, classifications=[]
        ),
        bos=[
            BOSEvidence(
                direction=Direction.BULLISH,
                break_price=Decimal("1.1050"),
                break_time=_CALCULATED_AT,
                strength=1.0,
                confirmed=True,
            )
        ],
        choch=[
            CHOCHEvidence(
                previous_trend=MarketStructureState.RANGE,
                new_trend=MarketStructureState.BULLISH,
                confidence=1.0,
                confirmation_time=_CALCULATED_AT,
            )
        ],
        order_blocks=[
            OrderBlockEvidence(
                direction=Direction.BULLISH,
                zone_high=Decimal("1.1050"),
                zone_low=Decimal("1.1000"),
                created_at=_CALCULATED_AT,
                status=SMCEventStatus.ACTIVE,
                touched=False,
                mitigated=False,
                broken=False,
                strength_score=50.0,
                freshness_score=50.0,
                volume_confirmed=True,
            )
        ],
        fair_value_gaps=[
            FairValueGapEvidence(
                direction=Direction.BULLISH,
                gap_high=Decimal("1.1050"),
                gap_low=Decimal("1.1000"),
                created_at=_CALCULATED_AT,
                status=SMCEventStatus.ACTIVE,
                gap_size=Decimal("0.0050"),
                priority="medium",
            )
        ],
        liquidity_zones=[
            LiquidityZoneEvidence(
                side=LiquiditySide.BUY_SIDE,
                level=Decimal("1.1050"),
                touch_count=1,
                status=SMCEventStatus.ACTIVE,
                created_at=_CALCULATED_AT,
            )
        ],
        liquidity_sweeps=[
            LiquiditySweepEvidence(
                side=LiquiditySide.BUY_SIDE,
                level=Decimal("1.1050"),
                sweep_time=_CALCULATED_AT,
                false_breakout=True,
            )
        ],
        premium_discount=PremiumDiscountEvidence(
            position=PremiumDiscountPosition.EQUILIBRIUM,
            distance=0.0,
            range_high=Decimal("1.1100"),
            range_low=Decimal("1.0900"),
            equilibrium=Decimal("1.1000"),
        ),
        confluence=ConfluenceEvidence(factors=[], confluence_score=0.0),
        score_breakdown=SMCScoreBreakdown(
            market_structure=30.0,
            order_blocks=12.0,
            fair_value_gaps=6.0,
            liquidity=6.0,
            premium_discount=6.0,
            confluence=0.0,
            penalties=0.0,
        ),
        warnings=[],
        calculated_at=_CALCULATED_AT,
    )


def test_check_all_five_present() -> None:
    evidence = make_evidence_bundle(smc=_full_smc_result())
    result = check(evidence)
    assert result.met_count == 5
    assert result.total_count == 5


def test_check_no_smc_evidence_gives_zero_met() -> None:
    evidence = make_evidence_bundle(include_evidence=False)
    result = check(evidence)
    assert result.met_count == 0
    assert result.total_count == 5


def test_check_default_smc_result_has_fewer_matches() -> None:
    """`make_smc_result()`'s default only populates `bos`, everything
    else defaults empty."""
    evidence = make_evidence_bundle()
    result = check(evidence)
    assert result.met_count == 1
    assert result.total_count == 5

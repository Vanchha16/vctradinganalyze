from app.services.market_regime import trend_regime_analyzer
from app.services.smc.types import MarketStructureEvidence, MarketStructureState
from app.services.technical_analysis.types import (
    MovingAverageEvidence,
    TrendDirection,
    TrendEvidence,
    TrendStrengthLevel,
)

_MOVING_AVERAGE = MovingAverageEvidence(
    price_above_ema20=True,
    price_above_ema50=True,
    price_above_ema100=True,
    price_above_ema200=True,
    price_above_sma200=True,
    bullish_alignment=True,
    bearish_alignment=False,
    alignment_score=1.0,
)


def _trend(
    direction: TrendDirection, strength: TrendStrengthLevel = TrendStrengthLevel.STRONG
) -> TrendEvidence:
    return TrendEvidence(
        direction=direction,
        strength=strength,
        adx=30.0,
        di_plus=25.0,
        di_minus=10.0,
        moving_average=_MOVING_AVERAGE,
    )


def test_aligned_when_ta_and_smc_agree_bullish() -> None:
    market_structure = MarketStructureEvidence(
        state=MarketStructureState.BULLISH, classifications=[]
    )

    evidence = trend_regime_analyzer.analyze(_trend(TrendDirection.BULLISH), market_structure)

    assert evidence.aligned is True
    assert evidence.direction == TrendDirection.BULLISH
    assert evidence.structure_state == MarketStructureState.BULLISH


def test_not_aligned_when_ta_and_smc_disagree() -> None:
    market_structure = MarketStructureEvidence(
        state=MarketStructureState.BEARISH, classifications=[]
    )

    evidence = trend_regime_analyzer.analyze(_trend(TrendDirection.BULLISH), market_structure)

    assert evidence.aligned is False


def test_not_aligned_when_smc_structure_is_range() -> None:
    market_structure = MarketStructureEvidence(state=MarketStructureState.RANGE, classifications=[])

    evidence = trend_regime_analyzer.analyze(_trend(TrendDirection.BEARISH), market_structure)

    assert evidence.aligned is False

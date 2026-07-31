from app.models.enums import Timeframe
from app.services.market_regime import multi_timeframe_analyzer
from app.services.market_regime.types import (
    MarketRegimeState,
    MarketRegimeVerdict,
    TimeframeRegimeSummary,
)


def test_bullish_alignment_when_higher_timeframes_trending_bullish() -> None:
    summaries = [
        TimeframeRegimeSummary(timeframe=Timeframe.W1, regime=MarketRegimeState.TRENDING_BULLISH),
        TimeframeRegimeSummary(timeframe=Timeframe.D1, regime=MarketRegimeState.TRENDING_BULLISH),
        TimeframeRegimeSummary(timeframe=Timeframe.H4, regime=MarketRegimeState.TRENDING_BULLISH),
        TimeframeRegimeSummary(timeframe=Timeframe.H1, regime=MarketRegimeState.RANGING),
        TimeframeRegimeSummary(timeframe=Timeframe.M15, regime=MarketRegimeState.TRENDING_BULLISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MarketRegimeVerdict.BULLISH_ALIGNMENT


def test_mixed_when_no_clear_majority() -> None:
    summaries = [
        TimeframeRegimeSummary(timeframe=Timeframe.W1, regime=MarketRegimeState.TRENDING_BULLISH),
        TimeframeRegimeSummary(timeframe=Timeframe.D1, regime=MarketRegimeState.TRENDING_BEARISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MarketRegimeVerdict.MIXED


def test_empty_summaries_is_mixed() -> None:
    assert multi_timeframe_analyzer.combine([]) == MarketRegimeVerdict.MIXED

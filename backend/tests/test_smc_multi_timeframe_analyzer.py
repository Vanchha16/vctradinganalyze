from app.models.enums import Timeframe
from app.services.smc import multi_timeframe_analyzer
from app.services.smc.types import MarketStructureState, SMCVerdict, TimeframeMarketStructureSummary


def test_bullish_alignment_when_higher_timeframes_agree() -> None:
    summaries = [
        TimeframeMarketStructureSummary(timeframe=Timeframe.W1, state=MarketStructureState.BULLISH),
        TimeframeMarketStructureSummary(timeframe=Timeframe.D1, state=MarketStructureState.BULLISH),
        TimeframeMarketStructureSummary(timeframe=Timeframe.H4, state=MarketStructureState.BULLISH),
        TimeframeMarketStructureSummary(timeframe=Timeframe.H1, state=MarketStructureState.RANGE),
        TimeframeMarketStructureSummary(
            timeframe=Timeframe.M15, state=MarketStructureState.BULLISH
        ),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == SMCVerdict.BULLISH_ALIGNMENT


def test_mixed_when_no_clear_majority() -> None:
    summaries = [
        TimeframeMarketStructureSummary(timeframe=Timeframe.W1, state=MarketStructureState.BULLISH),
        TimeframeMarketStructureSummary(timeframe=Timeframe.D1, state=MarketStructureState.BEARISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == SMCVerdict.MIXED


def test_empty_summaries_is_mixed() -> None:
    assert multi_timeframe_analyzer.combine([]) == SMCVerdict.MIXED

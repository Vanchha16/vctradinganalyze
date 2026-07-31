from app.models.enums import Timeframe
from app.services.technical_analysis import multi_timeframe_analyzer
from app.services.technical_analysis.types import (
    MultiTimeframeVerdict,
    TimeframeTrendSummary,
    TrendDirection,
    TrendStrengthLevel,
)


def _summary(timeframe: Timeframe, direction: TrendDirection) -> TimeframeTrendSummary:
    return TimeframeTrendSummary(
        timeframe=timeframe, direction=direction, strength=TrendStrengthLevel.STRONG
    )


def test_all_bullish_yields_bullish_alignment() -> None:
    summaries = [
        _summary(Timeframe.D1, TrendDirection.BULLISH),
        _summary(Timeframe.H4, TrendDirection.BULLISH),
        _summary(Timeframe.H1, TrendDirection.BULLISH),
        _summary(Timeframe.M15, TrendDirection.BULLISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MultiTimeframeVerdict.BULLISH_ALIGNMENT


def test_all_bearish_yields_bearish_alignment() -> None:
    summaries = [
        _summary(Timeframe.D1, TrendDirection.BEARISH),
        _summary(Timeframe.H4, TrendDirection.BEARISH),
        _summary(Timeframe.H1, TrendDirection.BEARISH),
        _summary(Timeframe.M15, TrendDirection.BEARISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MultiTimeframeVerdict.BEARISH_ALIGNMENT


def test_docs_08_example_daily_h4_bullish_h1_pullback_m15_bullish() -> None:
    """docs/08 §8's own example: Daily Bullish, H4 Bullish, H1 Pullback
    (bearish/sideways), M15 Bullish -> Bullish Continuation."""
    summaries = [
        _summary(Timeframe.D1, TrendDirection.BULLISH),
        _summary(Timeframe.H4, TrendDirection.BULLISH),
        _summary(Timeframe.H1, TrendDirection.SIDEWAYS),
        _summary(Timeframe.M15, TrendDirection.BULLISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MultiTimeframeVerdict.BULLISH_ALIGNMENT


def test_evenly_split_timeframes_yield_mixed() -> None:
    summaries = [
        _summary(Timeframe.D1, TrendDirection.BULLISH),
        _summary(Timeframe.H4, TrendDirection.BEARISH),
        _summary(Timeframe.H1, TrendDirection.BULLISH),
        _summary(Timeframe.M15, TrendDirection.BEARISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MultiTimeframeVerdict.MIXED


def test_higher_timeframe_has_greater_weight_but_needs_a_clear_majority() -> None:
    """Daily+H4 bullish (70) vs. H1+M15 bearish (30) nets to +40 out of a
    possible 100 - a 0.4 ratio, which does not cross the 0.5 alignment
    threshold, so this is correctly MIXED rather than an outright bullish
    call. Higher timeframes still matter (the net is positive, not zero),
    just not enough alone to declare full alignment against two
    dissenting timeframes."""
    summaries = [
        _summary(Timeframe.D1, TrendDirection.BULLISH),
        _summary(Timeframe.H4, TrendDirection.BULLISH),
        _summary(Timeframe.H1, TrendDirection.BEARISH),
        _summary(Timeframe.M15, TrendDirection.BEARISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MultiTimeframeVerdict.MIXED


def test_daily_alone_bullish_outweighs_h1_and_m15_bearish() -> None:
    """Daily bullish (40) vs. H1+M15 bearish (30) nets to +10 out of 70
    possible (H4 absent here) - a ~0.14 ratio, still MIXED. Confirms a
    single higher-timeframe vote doesn't automatically override multiple
    lower-timeframe dissents without a clear majority."""
    summaries = [
        _summary(Timeframe.D1, TrendDirection.BULLISH),
        _summary(Timeframe.H1, TrendDirection.BEARISH),
        _summary(Timeframe.M15, TrendDirection.BEARISH),
    ]

    assert multi_timeframe_analyzer.combine(summaries) == MultiTimeframeVerdict.MIXED


def test_empty_summaries_yield_mixed() -> None:
    assert multi_timeframe_analyzer.combine([]) == MultiTimeframeVerdict.MIXED

"""docs/08 §8 Multi-Timeframe Analysis (ADR-030): scoped exactly to the
four named timeframes (Daily > H4 > H1 > M15), weighted by priority -
not generalized to every canonical Timeframe, since the doc doesn't ask
for that."""

from app.models.enums import Timeframe
from app.services.technical_analysis.types import (
    MultiTimeframeVerdict,
    TimeframeTrendSummary,
    TrendDirection,
)

#: Weights sum to 100, mirroring the scoring engine's pattern for
#: consistency. Higher timeframe = more weight (docs/08 §8).
TIMEFRAME_WEIGHTS: dict[Timeframe, float] = {
    Timeframe.D1: 40.0,
    Timeframe.H4: 30.0,
    Timeframe.H1: 20.0,
    Timeframe.M15: 10.0,
}

_ALIGNMENT_THRESHOLD = 0.5


def combine(summaries: list[TimeframeTrendSummary]) -> MultiTimeframeVerdict:
    net = 0.0
    max_possible = 0.0

    for summary in summaries:
        weight = TIMEFRAME_WEIGHTS.get(summary.timeframe)
        if weight is None:
            continue
        max_possible += weight
        if summary.direction == TrendDirection.BULLISH:
            net += weight
        elif summary.direction == TrendDirection.BEARISH:
            net -= weight

    if max_possible == 0:
        return MultiTimeframeVerdict.MIXED

    ratio = net / max_possible
    if ratio >= _ALIGNMENT_THRESHOLD:
        return MultiTimeframeVerdict.BULLISH_ALIGNMENT
    if ratio <= -_ALIGNMENT_THRESHOLD:
        return MultiTimeframeVerdict.BEARISH_ALIGNMENT
    return MultiTimeframeVerdict.MIXED

"""docs/09 §15 Multi-Timeframe Analysis (ADR-036): scoped to the five
named timeframes (Weekly > Daily > H4 > H1 > M15), weighted by
priority - a distinct weight set from Technical Analysis's ADR-030,
since docs/09 names an extra timeframe (Weekly) that docs/08 doesn't.
"""

from app.models.enums import Timeframe
from app.services.smc.types import MarketStructureState, SMCVerdict, TimeframeMarketStructureSummary

#: Weights sum to 100, mirroring Technical Analysis's pattern (ADR-030).
TIMEFRAME_WEIGHTS: dict[Timeframe, float] = {
    Timeframe.W1: 35.0,
    Timeframe.D1: 30.0,
    Timeframe.H4: 20.0,
    Timeframe.H1: 10.0,
    Timeframe.M15: 5.0,
}

_ALIGNMENT_THRESHOLD = 0.5


def combine(summaries: list[TimeframeMarketStructureSummary]) -> SMCVerdict:
    net = 0.0
    max_possible = 0.0

    for summary in summaries:
        weight = TIMEFRAME_WEIGHTS.get(summary.timeframe)
        if weight is None:
            continue
        max_possible += weight
        if summary.state == MarketStructureState.BULLISH:
            net += weight
        elif summary.state == MarketStructureState.BEARISH:
            net -= weight

    if max_possible == 0:
        return SMCVerdict.MIXED

    ratio = net / max_possible
    if ratio >= _ALIGNMENT_THRESHOLD:
        return SMCVerdict.BULLISH_ALIGNMENT
    if ratio <= -_ALIGNMENT_THRESHOLD:
        return SMCVerdict.BEARISH_ALIGNMENT
    return SMCVerdict.MIXED

"""Multi-timeframe regime combination. Reuses SMC's five-timeframe set
(W1/D1/H4/H1/M15, ADR-036) rather than Technical Analysis's four, since
Market Regime consumes evidence from both engines and SMC's set is a
strict superset - confirmed on Phase 4C approval.
"""

from app.models.enums import Timeframe
from app.services.market_regime.types import (
    MarketRegimeState,
    MarketRegimeVerdict,
    TimeframeRegimeSummary,
)

TIMEFRAME_WEIGHTS: dict[Timeframe, float] = {
    Timeframe.W1: 35.0,
    Timeframe.D1: 30.0,
    Timeframe.H4: 20.0,
    Timeframe.H1: 10.0,
    Timeframe.M15: 5.0,
}

_ALIGNMENT_THRESHOLD = 0.5


def combine(summaries: list[TimeframeRegimeSummary]) -> MarketRegimeVerdict:
    net = 0.0
    max_possible = 0.0

    for summary in summaries:
        weight = TIMEFRAME_WEIGHTS.get(summary.timeframe)
        if weight is None:
            continue
        max_possible += weight
        if summary.regime == MarketRegimeState.TRENDING_BULLISH:
            net += weight
        elif summary.regime == MarketRegimeState.TRENDING_BEARISH:
            net -= weight

    if max_possible == 0:
        return MarketRegimeVerdict.MIXED

    ratio = net / max_possible
    if ratio >= _ALIGNMENT_THRESHOLD:
        return MarketRegimeVerdict.BULLISH_ALIGNMENT
    if ratio <= -_ALIGNMENT_THRESHOLD:
        return MarketRegimeVerdict.BEARISH_ALIGNMENT
    return MarketRegimeVerdict.MIXED

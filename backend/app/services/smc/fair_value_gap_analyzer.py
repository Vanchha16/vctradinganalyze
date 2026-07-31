"""docs/09 §9 Fair Value Gaps: classic 3-candle gap detection. A bullish
FVG exists when candle[i-2]'s high sits below candle[i]'s low (the
middle candle's displacement leaves an untraded gap); a bearish FVG is
the mirror. `priority` is the gap's size relative to the displacement
candle's own range - a simple, deterministic proxy for significance.

Fill-state is checked against the *same* candle window right away
(rather than via a separate consumer analyzer, unlike Order Blocks)
since it only needs the raw candles, not another analyzer's evidence.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.models.price_candle import PriceCandle
from app.services.smc.types import Direction, FairValueGapEvidence

_HIGH_PRIORITY_RATIO = Decimal("0.5")
_MEDIUM_PRIORITY_RATIO = Decimal("0.2")


def _priority(gap_size: Decimal, middle_candle: PriceCandle) -> str:
    middle_range = middle_candle.high - middle_candle.low
    if middle_range <= 0:
        return "low"
    ratio = gap_size / middle_range
    if ratio > _HIGH_PRIORITY_RATIO:
        return "high"
    if ratio > _MEDIUM_PRIORITY_RATIO:
        return "medium"
    return "low"


def _is_filled(candles: Sequence[PriceCandle], gap_low: Decimal, gap_high: Decimal) -> bool:
    return any(candle.low <= gap_low and candle.high >= gap_high for candle in candles)


def analyze(candles: Sequence[PriceCandle]) -> list[FairValueGapEvidence]:
    gaps: list[FairValueGapEvidence] = []

    for i in range(2, len(candles)):
        first, middle, third = candles[i - 2], candles[i - 1], candles[i]
        subsequent = candles[i + 1 :]

        if first.high < third.low:
            gap_low, gap_high = first.high, third.low
            gap_size = gap_high - gap_low
            status = (
                SMCEventStatus.MITIGATED
                if _is_filled(subsequent, gap_low, gap_high)
                else SMCEventStatus.ACTIVE
            )
            gaps.append(
                FairValueGapEvidence(
                    direction=Direction.BULLISH,
                    gap_high=gap_high,
                    gap_low=gap_low,
                    created_at=middle.timestamp,
                    status=status,
                    gap_size=gap_size,
                    priority=_priority(gap_size, middle),
                )
            )
        elif first.low > third.high:
            gap_high, gap_low = first.low, third.high
            gap_size = gap_high - gap_low
            status = (
                SMCEventStatus.MITIGATED
                if _is_filled(subsequent, gap_low, gap_high)
                else SMCEventStatus.ACTIVE
            )
            gaps.append(
                FairValueGapEvidence(
                    direction=Direction.BEARISH,
                    gap_high=gap_high,
                    gap_low=gap_low,
                    created_at=middle.timestamp,
                    status=status,
                    gap_size=gap_size,
                    priority=_priority(gap_size, middle),
                )
            )

    return gaps

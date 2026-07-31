"""docs/09 §7 Change of Character: the first genuine reversal between
Bullish and Bearish market structure (not merely a dip into Range or
Transition). Confidence is derived from the confirming BOS's strength;
if no BOS confirms the reversal by the time it's detected, a lower
default confidence is used.
"""

from collections.abc import Sequence
from datetime import datetime

from app.models.price_candle import PriceCandle
from app.services.smc import bos_analyzer
from app.services.smc.market_structure_analyzer import (
    classify_swings,
    state_from_last_classifications,
)
from app.services.smc.types import BOSEvidence, CHOCHEvidence, Direction, MarketStructureState

_REVERSAL_PAIR = {MarketStructureState.BULLISH, MarketStructureState.BEARISH}
_DEFAULT_CONFIDENCE = 0.5
_STRENGTH_CONFIDENCE_SCALE = 5.0


def _confirming_bos(
    bos_events: Sequence[BOSEvidence], since: datetime, direction: Direction
) -> BOSEvidence | None:
    for event in bos_events:
        if event.break_time >= since and event.direction == direction:
            return event
    return None


def analyze(candles: Sequence[PriceCandle]) -> list[CHOCHEvidence]:
    high_classifications, low_classifications = classify_swings(candles)
    bos_events = bos_analyzer.analyze(candles)

    timeline = sorted(
        [(c.timestamp, "high", c.kind) for c in high_classifications]
        + [(c.timestamp, "low", c.kind) for c in low_classifications],
        key=lambda item: item[0],
    )

    running_high_kind: str | None = None
    running_low_kind: str | None = None
    previous_state = MarketStructureState.RANGE
    choch_events: list[CHOCHEvidence] = []

    for timestamp, kind_group, kind in timeline:
        if kind_group == "high":
            running_high_kind = kind
        else:
            running_low_kind = kind

        new_state = state_from_last_classifications(running_high_kind, running_low_kind)

        if new_state != previous_state and {previous_state, new_state} == _REVERSAL_PAIR:
            direction = (
                Direction.BULLISH
                if new_state == MarketStructureState.BULLISH
                else Direction.BEARISH
            )
            confirming = _confirming_bos(bos_events, timestamp, direction)
            confidence = (
                min(1.0, confirming.strength / _STRENGTH_CONFIDENCE_SCALE)
                if confirming is not None
                else _DEFAULT_CONFIDENCE
            )
            confirmation_time = confirming.break_time if confirming is not None else timestamp
            choch_events.append(
                CHOCHEvidence(
                    previous_trend=previous_state,
                    new_trend=new_state,
                    confidence=confidence,
                    confirmation_time=confirmation_time,
                )
            )

        if new_state in _REVERSAL_PAIR:
            previous_state = new_state

    return choch_events

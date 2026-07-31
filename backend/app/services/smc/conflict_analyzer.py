"""docs/09 §16 Conflict Detection: a lower timeframe disagreeing with a
higher timeframe's market structure is classified as a Pullback, not a
full reversal, unless/until confirmed otherwise (e.g. by a CHOCH on the
lower timeframe - left to a future phase to wire in as a stronger
signal; today this analyzer only flags the disagreement).
"""

from app.services.smc.types import MarketStructureState, SMCConflictReport

_DIRECTIONAL = {MarketStructureState.BULLISH, MarketStructureState.BEARISH}


def analyze(
    higher_timeframe_state: MarketStructureState, lower_timeframe_state: MarketStructureState
) -> SMCConflictReport:
    if (
        higher_timeframe_state not in _DIRECTIONAL
        or lower_timeframe_state not in _DIRECTIONAL
        or higher_timeframe_state == lower_timeframe_state
    ):
        return SMCConflictReport(is_pullback=False, conflicts=[])

    conflict = f"higher_{higher_timeframe_state.value}_lower_{lower_timeframe_state.value}"
    return SMCConflictReport(is_pullback=True, conflicts=[conflict])

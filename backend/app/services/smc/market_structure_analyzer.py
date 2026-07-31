"""docs/09 §5 Market Structure: classify each swing point relative to the
prior swing of the same type (HH/HL vs LH/LL), then derive an overall
structure state from the most recent classifications of each type.

Reuses the shared `find_swing_points` fractal detector (also used by
Technical Analysis's `SupportResistanceAnalyzer`) rather than
re-implementing swing detection for SMC. `classify_swings` is exported
so `choch_analyzer` can replay the same classification timeline without
duplicating this logic.
"""

from collections.abc import Sequence

from app.models.price_candle import PriceCandle
from app.services.market_structure.swing_points import SwingPoint, find_swing_points
from app.services.smc.types import (
    MarketStructureEvidence,
    MarketStructureState,
    SwingClassification,
)


def _classify(
    kind_pair: tuple[str, str], points: Sequence[SwingPoint]
) -> list[SwingClassification]:
    higher_kind, lower_kind = kind_pair
    classifications: list[SwingClassification] = []
    for i in range(1, len(points)):
        kind = higher_kind if points[i].price > points[i - 1].price else lower_kind
        classifications.append(
            SwingClassification(
                kind=kind,
                price=points[i].price,
                timestamp=points[i].timestamp,
                index=points[i].index,
            )
        )
    return classifications


def classify_swings(
    candles: Sequence[PriceCandle],
) -> tuple[list[SwingClassification], list[SwingClassification]]:
    """Returns (high_classifications, low_classifications), each sorted
    oldest-first, each already labeled hh/lh or hl/ll respectively."""
    swing_highs, swing_lows = find_swing_points(candles)
    return _classify(("hh", "lh"), swing_highs), _classify(("hl", "ll"), swing_lows)


def state_from_last_classifications(
    last_high_kind: str | None, last_low_kind: str | None
) -> MarketStructureState:
    if last_high_kind is None or last_low_kind is None:
        return MarketStructureState.RANGE
    if last_high_kind == "hh" and last_low_kind == "hl":
        return MarketStructureState.BULLISH
    if last_high_kind == "lh" and last_low_kind == "ll":
        return MarketStructureState.BEARISH
    return MarketStructureState.TRANSITION


def analyze(candles: Sequence[PriceCandle]) -> MarketStructureEvidence:
    high_classifications, low_classifications = classify_swings(candles)

    all_classifications = sorted(
        [*high_classifications, *low_classifications], key=lambda c: c.timestamp
    )

    state = state_from_last_classifications(
        high_classifications[-1].kind if high_classifications else None,
        low_classifications[-1].kind if low_classifications else None,
    )

    return MarketStructureEvidence(state=state, classifications=all_classifications)

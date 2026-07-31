"""docs/16 §11/§12. Reversal reuses SMC's `CHOCHEvidence` directly (the
"CHOCH"/"Momentum Shift" requirement). Pullback depth is a
single-timeframe retracement-depth measurement (ADR-041) - distinct
from SMC's multi-timeframe Pullback (ADR-036/docs/09 §16) - using the
most recently classified swing high/low from SMC's
`MarketStructureEvidence` (not re-detected here) to define the current
swing leg, with Fibonacci-style retracement bands (0.382/0.618).

docs/16 §2's undocumented "exhaustion" responsibility is folded in as
a warning here (a deep, unconfirmed retracement), not a dedicated
analyzer or regime value - nothing in docs/16 defines it precisely
enough to justify more than that.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.services.market_regime.types import (
    PullbackDepth,
    PullbackReversalEvidence,
    ReversalDirection,
)
from app.services.smc.types import CHOCHEvidence, MarketStructureState, SwingClassification
from app.services.technical_analysis.types import TrendDirection

_HEALTHY_MAX_RATIO = 0.382
_DEEP_MAX_RATIO = 0.618


def _latest_reversal(
    choch_events: Sequence[CHOCHEvidence],
) -> tuple[ReversalDirection | None, float | None]:
    if not choch_events:
        return None, None
    latest = choch_events[-1]
    if latest.new_trend == MarketStructureState.BULLISH:
        return ReversalDirection.BULLISH, latest.confidence * 100
    if latest.new_trend == MarketStructureState.BEARISH:
        return ReversalDirection.BEARISH, latest.confidence * 100
    return None, None


def analyze(
    trend_direction: TrendDirection,
    classifications: Sequence[SwingClassification],
    current_price: Decimal,
    choch_events: Sequence[CHOCHEvidence],
) -> PullbackReversalEvidence:
    reversal_direction, reversal_confidence = _latest_reversal(choch_events)

    highs = [c for c in classifications if c.kind in ("hh", "lh")]
    lows = [c for c in classifications if c.kind in ("hl", "ll")]

    pullback_depth: PullbackDepth | None = None
    retracement_ratio: float | None = None

    if highs and lows and trend_direction in (TrendDirection.BULLISH, TrendDirection.BEARISH):
        latest_high = highs[-1].price
        latest_low = lows[-1].price
        swing_range = latest_high - latest_low

        if swing_range > 0:
            if trend_direction == TrendDirection.BULLISH:
                retracement_ratio = float((latest_high - current_price) / swing_range)
            else:
                retracement_ratio = float((current_price - latest_low) / swing_range)

            if retracement_ratio <= _HEALTHY_MAX_RATIO:
                pullback_depth = PullbackDepth.HEALTHY
            elif retracement_ratio <= _DEEP_MAX_RATIO:
                pullback_depth = PullbackDepth.DEEP
            else:
                pullback_depth = PullbackDepth.POTENTIAL_REVERSAL

    exhaustion_warning = None
    if (
        retracement_ratio is not None
        and retracement_ratio > _DEEP_MAX_RATIO
        and reversal_direction is None
    ):
        exhaustion_warning = (
            "Momentum exhaustion detected: deep retracement without a confirmed reversal"
        )

    return PullbackReversalEvidence(
        pullback_depth=pullback_depth,
        retracement_ratio=retracement_ratio,
        reversal_direction=reversal_direction,
        reversal_confidence=reversal_confidence,
        exhaustion_warning=exhaustion_warning,
    )

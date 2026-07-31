"""Within-window regime-shift detection. Since the engine is stateless
(ADR-038), there is no persisted prior classification to diff against -
this analyzer instead compares the first half of the current lookback
window to the second half (both for price direction and for volatility,
reusing `ExpansionAnalyzer`'s already-computed state rather than a
third pass over the candles).
"""

from collections.abc import Sequence
from decimal import Decimal

from app.models.price_candle import PriceCandle
from app.services.market_regime.types import (
    ExpansionEvidence,
    ExpansionState,
    MarketRegimeState,
    TransitionEvidence,
)

_MIN_CANDLES = 20
_SIDEWAYS_TOLERANCE = Decimal("0.002")  # 20 basis points


def _direction_bias(closes: Sequence[float]) -> str:
    if not closes:
        return "sideways"
    start, end = Decimal(str(closes[0])), Decimal(str(closes[-1]))
    if start == 0:
        return "sideways"
    change_ratio = (end - start) / start
    if change_ratio > _SIDEWAYS_TOLERANCE:
        return "bullish"
    if change_ratio < -_SIDEWAYS_TOLERANCE:
        return "bearish"
    return "sideways"


def _hint_from_bias(bias: str) -> MarketRegimeState:
    if bias == "bullish":
        return MarketRegimeState.TRENDING_BULLISH
    if bias == "bearish":
        return MarketRegimeState.TRENDING_BEARISH
    return MarketRegimeState.RANGING


def analyze(candles: Sequence[PriceCandle], expansion: ExpansionEvidence) -> TransitionEvidence:
    if len(candles) < _MIN_CANDLES:
        return TransitionEvidence(shifting=False, from_hint=None, to_hint=None, confidence=0.0)

    closes = [float(c.close) for c in candles]
    midpoint = len(closes) // 2
    first_bias = _direction_bias(closes[:midpoint])
    second_bias = _direction_bias(closes[midpoint:])

    price_shift = first_bias != second_bias
    volatility_shift = expansion.state != ExpansionState.STABLE

    confidence = (50.0 if price_shift else 0.0) + (50.0 if volatility_shift else 0.0)

    return TransitionEvidence(
        shifting=price_shift or volatility_shift,
        from_hint=_hint_from_bias(first_bias) if price_shift else None,
        to_hint=_hint_from_bias(second_bias) if price_shift else None,
        confidence=min(100.0, confidence),
    )

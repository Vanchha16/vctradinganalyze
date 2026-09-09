"""Deterministic candidate-setup construction (docs/50 §6, ADR-080).
Resolves the chicken-and-egg problem: Risk Management needs a candidate
trade to evaluate, but nothing upstream produces one. Builds a candidate
ONLY if Strategy Engine has a viable primary strategy and Market Regime's
trend direction is unambiguous - never fabricates a price, only derives
entry/stop/target from already-computed Technical Analysis/SMC evidence.
"""

from decimal import Decimal

from app.services.analysis_confidence.types import ConfidenceResult
from app.services.risk_management.types import TradeDirection
from app.services.strategy.types import StrategyEvaluation
from app.services.technical_analysis.types import TrendDirection

from .types import CandidateSetup

_STOP_ATR_MULTIPLE = Decimal("1.5")
_MIN_RISK_REWARD_MULTIPLE = Decimal("2")


def _direction_for(confidence: ConfidenceResult) -> TradeDirection | None:
    if confidence.market_regime is None:
        return None
    trend_direction = confidence.market_regime.trend_regime.direction
    if trend_direction is TrendDirection.BULLISH:
        return TradeDirection.LONG
    if trend_direction is TrendDirection.BEARISH:
        return TradeDirection.SHORT
    return None


def _more_conservative_long_stop(
    entry_price: Decimal, structural_stop: Decimal | None, atr_stop_distance: Decimal | None
) -> Decimal | None:
    candidates: list[Decimal] = []
    if structural_stop is not None and structural_stop < entry_price:
        candidates.append(structural_stop)
    if atr_stop_distance is not None:
        candidates.append(entry_price - atr_stop_distance)
    if not candidates:
        return None
    return min(candidates)  # further from entry = more conservative for a long stop


def _more_conservative_short_stop(
    entry_price: Decimal, structural_stop: Decimal | None, atr_stop_distance: Decimal | None
) -> Decimal | None:
    candidates: list[Decimal] = []
    if structural_stop is not None and structural_stop > entry_price:
        candidates.append(structural_stop)
    if atr_stop_distance is not None:
        candidates.append(entry_price + atr_stop_distance)
    if not candidates:
        return None
    return max(candidates)


def _further_target_long(
    entry_price: Decimal, min_reward_distance: Decimal, structural_target: Decimal | None
) -> Decimal:
    min_target = entry_price + min_reward_distance
    if structural_target is not None and structural_target > min_target:
        return structural_target
    return min_target


def _further_target_short(
    entry_price: Decimal, min_reward_distance: Decimal, structural_target: Decimal | None
) -> Decimal:
    min_target = entry_price - min_reward_distance
    if structural_target is not None and structural_target < min_target:
        return structural_target
    return min_target


def build(
    confidence: ConfidenceResult,
    strategy: StrategyEvaluation,
    latest_close: Decimal | None,
) -> CandidateSetup | None:
    """`latest_close` is the real most-recent traded price, supplied by
    the caller (ADR-145).

    It used to be derived here as the midpoint of support and
    resistance, in a helper *named* `_latest_close` whose docstring
    claimed to approximate the latest close. It did not: the midpoint of
    a range only equals the price when price happens to sit mid-range.

    That failed systematically rather than randomly, because a candidate
    is only built when Market Regime reports an unambiguous trend
    (`_direction_for`) - and in a trend price sits near a range
    *extreme*, not its middle. In a downtrend the midpoint therefore
    lands above price, producing a SELL entry above market that only
    fills on a rally. Measured on production over 14 days: 10 of 14
    entries were on the unfillable side of the market, gaps up to 45.65
    points, and the 4 signals that never filled had the largest gaps.

    Every other level is derived from `entry_price`, so a wrong entry
    also moved the stop, the target, and the real (as opposed to
    nominal) risk/reward of every signal this project has produced.
    """
    if strategy.primary_strategy is None or confidence.technical is None:
        return None

    direction = _direction_for(confidence)
    if direction is None:
        return None

    technical = confidence.technical
    #: No price, no candidate. Deliberately not falling back to the old
    #: midpoint: a silent fallback to a known-wrong entry is worse than
    #: producing no setup (which yields WAIT, ADR-011). Near-unreachable
    #: in practice - `confidence.technical` only exists if the same
    #: candles this price comes from were present.
    entry_price = latest_close
    if entry_price is None:
        return None

    atr = technical.volatility.atr
    atr_stop_distance = (
        Decimal(str(atr)) * _STOP_ATR_MULTIPLE if atr is not None and atr > 0 else None
    )

    if direction is TradeDirection.LONG:
        structural_stop = technical.support.price if technical.support is not None else None
        stop_loss = _more_conservative_long_stop(entry_price, structural_stop, atr_stop_distance)
    else:
        structural_stop = technical.resistance.price if technical.resistance is not None else None
        stop_loss = _more_conservative_short_stop(entry_price, structural_stop, atr_stop_distance)

    if stop_loss is None:
        return None

    risk_distance = abs(entry_price - stop_loss)
    if risk_distance == 0:
        return None

    min_reward_distance = risk_distance * _MIN_RISK_REWARD_MULTIPLE
    if direction is TradeDirection.LONG:
        structural_target = technical.resistance.price if technical.resistance is not None else None
        take_profit = _further_target_long(entry_price, min_reward_distance, structural_target)
    else:
        structural_target = technical.support.price if technical.support is not None else None
        take_profit = _further_target_short(entry_price, min_reward_distance, structural_target)

    return CandidateSetup(
        direction=direction, entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit
    )

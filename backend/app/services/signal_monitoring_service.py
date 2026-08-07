"""Pure entry-trigger and Take Profit / Stop Loss touch-detection logic
(docs/51 §10's deferred "live price-monitoring, trigger-detection, and
outcome tracking", completed by ADR-137). No DB/IO - mirrors
`risk_management/session_classifier.py`'s shape. Callers
(`workers/signal_monitoring_tasks.py`) own persistence."""

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import SignalStatus, SignalType
from app.models.price_candle import PriceCandle
from app.models.signal import Signal


@dataclass(frozen=True, slots=True)
class SignalOutcome:
    status: SignalStatus
    closed_price: Decimal
    profit_loss: Decimal


def entry_touched(signal: Signal, candle: PriceCandle) -> bool:
    """ADR-137's touch-based trigger rule: price has traded through the
    signal's entry level once `candle.low <= entry <= candle.high` -
    mirrors a limit order actually filling, symmetric with the
    touch-based SL/TP check below, no tolerance band."""
    return candle.low <= signal.entry_price <= candle.high


def evaluate_signal_outcome(signal: Signal, candle: PriceCandle) -> SignalOutcome | None:
    """Only meaningful for a `TRIGGERED` signal (ADR-137) - price must
    have already reached `entry_price` before SL/TP can be evaluated;
    the caller is responsible for that gating. Returns `None` if neither
    level was touched by `candle`'s high/low range. If both are touched
    within the same candle (a gap/spike, or the same candle that also
    triggered entry), Stop Loss takes precedence - the conservative
    assumption, consistent with never overstating a win."""
    if signal.signal_type == SignalType.BUY:
        hit_sl = candle.low <= signal.stop_loss
        hit_tp = candle.high >= signal.take_profit
    else:
        hit_sl = candle.high >= signal.stop_loss
        hit_tp = candle.low <= signal.take_profit

    if hit_sl:
        return _build_outcome(signal, SignalStatus.STOPPED_OUT, signal.stop_loss)
    if hit_tp:
        return _build_outcome(signal, SignalStatus.SUCCESSFUL, signal.take_profit)
    return None


def _build_outcome(signal: Signal, status: SignalStatus, closed_price: Decimal) -> SignalOutcome:
    if signal.signal_type == SignalType.BUY:
        profit_loss = closed_price - signal.entry_price
    else:
        profit_loss = signal.entry_price - closed_price
    return SignalOutcome(status=status, closed_price=closed_price, profit_loss=profit_loss)


__all__ = ["SignalOutcome", "entry_touched", "evaluate_signal_outcome"]

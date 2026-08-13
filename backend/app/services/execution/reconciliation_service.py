"""Reconciles a `BrokerOrder`-backed signal's status using the bridge's
own real position state, instead of the candle-simulated touch logic
every other signal uses (EA Bot spec §6).

Only ever called for a signal that already has a `BrokerOrder` row -
existence of that row is the fork condition `signal_monitoring_tasks.py`
checks before choosing this path over the existing simulated one; a
signal with no `BrokerOrder` is completely unaffected by this module.

Given §3D's max-1-concurrent-position rule, a single open position for
`order.symbol` is unambiguously this order's position - no separate
order-id-to-position-id lookup is needed (and none is exposed cheaply by
`get_open_positions` in the first place).

**Known, deliberate simplification (flagged, not silent):** the exact
SUCCESSFUL/STOPPED_OUT classification on close still comes from the
existing candle-based `evaluate_signal_outcome` (comparing the latest M1
candle's high/low against stop_loss/take_profit), not from the broker's
own deal/profit record (`get_deals_by_position`, unused here). What *is*
broker-driven is the trigger for re-checking: whether a real position is
currently open for this symbol, not a simulated "did price touch the
entry/stop/target" check. A full broker-P&L reconciliation is deferred,
same as this spec's other explicitly-deferred items (§9).
"""

from datetime import datetime
from decimal import Decimal

import structlog

from app.models.broker_order import BrokerOrder
from app.models.enums import OrderStatus, SignalStatus
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.repositories.broker_order_repository import BrokerOrderRepository
from app.services.execution.exceptions import TransientExecutionError
from app.services.execution.providers.base import OrderExecutionProvider
from app.services.signal_monitoring_service import evaluate_signal_outcome

logger = structlog.get_logger(__name__)


def reconcile_signal(
    signal: Signal,
    order: BrokerOrder,
    candle: PriceCandle | None,
    provider: OrderExecutionProvider,
    broker_order_repository: BrokerOrderRepository,
    now: datetime,
) -> None:
    try:
        positions = provider.get_open_positions(order.symbol)
    except TransientExecutionError:
        logger.warning(
            "execution.reconciliation_unavailable", signal_id=str(signal.id), exc_info=True
        )
        return

    matching = next((p for p in positions if p.direction == signal.signal_type), None)

    if matching is not None:
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.FILLED
            order.filled_price = Decimal(str(matching.open_price))
            order.filled_at = now
        if signal.status == SignalStatus.ACTIVE:
            signal.status = SignalStatus.TRIGGERED
            signal.triggered_at = now
            broker_order_repository.commit()
            logger.info("execution.signal_triggered_by_broker", signal_id=str(signal.id))

            from app.workers.telegram_tasks import enqueue_signal_triggered_delivery

            enqueue_signal_triggered_delivery(str(signal.id))
        return

    # No open position for this symbol anymore - if this order was
    # previously filled and the signal was live, the position has
    # closed on the broker side (SL/TP hit, or a manual close).
    if order.status != OrderStatus.FILLED or signal.status != SignalStatus.TRIGGERED:
        return

    if candle is None:
        # Can't classify SUCCESSFUL vs STOPPED_OUT without a price
        # reference - leave both rows as-is and re-check next tick
        # rather than guessing.
        return

    outcome = evaluate_signal_outcome(signal, candle)
    if outcome is None:
        # The broker says the position is gone, but our own candle data
        # doesn't yet show price having reached SL or TP - a real
        # divergence between the two sources of truth (§6's own warning:
        # "must not leave two disagreeing sources of truth unreconciled").
        # Logged, not silently resolved either way.
        logger.warning(
            "execution.reconciliation_outcome_mismatch",
            signal_id=str(signal.id),
            reason="broker reports position closed but candle-based SL/TP check found no outcome",
        )
        return

    signal.status = outcome.status
    signal.closed_at = now
    signal.profit_loss = outcome.profit_loss
    order.status = OrderStatus.CLOSED
    order.closed_at = now
    broker_order_repository.commit()
    logger.info(
        "execution.signal_closed_by_broker", signal_id=str(signal.id), status=outcome.status.value
    )

    from app.workers.telegram_tasks import enqueue_signal_outcome_delivery

    enqueue_signal_outcome_delivery(str(signal.id))


__all__ = ["reconcile_signal"]

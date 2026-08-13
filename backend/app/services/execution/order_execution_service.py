"""Ties a persisted `Signal` to a real (or dry-run) broker order (EA Bot
spec §3A/§3G/§12). Called once, immediately after `SignalEngine` persists
an actionable BUY/SELL signal (§1's hook point) - never retried
automatically; a signal this service could not execute for stays
`ACTIVE` and un-executed, same as any other signal today.
"""

from decimal import Decimal

import structlog

from app.models.asset import Asset
from app.models.broker_order import BrokerOrder
from app.models.enums import OrderStatus
from app.models.signal import Signal
from app.repositories.broker_order_repository import BrokerOrderRepository
from app.services.execution.exceptions import (
    PermanentExecutionError,
    PositionSizingRejectedError,
    TransientExecutionError,
)
from app.services.execution.position_sizing import calculate_position_size
from app.services.execution.providers.base import OrderExecutionProvider

logger = structlog.get_logger(__name__)


class OrderExecutionService:
    def __init__(
        self,
        provider: OrderExecutionProvider,
        broker_order_repository: BrokerOrderRepository,
        *,
        execution_enabled: bool,
        execution_symbol: str,
        risk_percent: Decimal,
        max_open_positions: int,
    ) -> None:
        self._provider = provider
        self._broker_order_repository = broker_order_repository
        self._execution_enabled = execution_enabled
        self._execution_symbol = execution_symbol
        self._risk_percent = risk_percent
        self._max_open_positions = max_open_positions

    def process_signal(self, signal: Signal, asset: Asset) -> BrokerOrder | None:
        """Returns the created `BrokerOrder` if a real order was placed
        (or rejected by the broker - still recorded), `None` for every
        other outcome (wrong symbol, max positions reached, sizing
        rejected, transient bridge failure, or - the default state,
        `EXECUTION_ENABLED=False` - a dry-run log only, §12)."""
        if asset.symbol != self._execution_symbol:
            return None

        try:
            account = self._provider.get_account_snapshot()
            spec = self._provider.get_symbol_specification(self._execution_symbol)
            open_positions = self._provider.get_open_positions(self._execution_symbol)
        except TransientExecutionError:
            logger.warning(
                "execution.account_data_unavailable", signal_id=str(signal.id), exc_info=True
            )
            return None

        if len(open_positions) >= self._max_open_positions:
            logger.info(
                "execution.max_open_positions_reached",
                signal_id=str(signal.id),
                open_positions=len(open_positions),
                max_open_positions=self._max_open_positions,
            )
            return None

        try:
            sizing = calculate_position_size(
                account=account,
                spec=spec,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                risk_percent=self._risk_percent,
            )
        except PositionSizingRejectedError as exc:
            logger.warning(
                "execution.position_sizing_rejected", signal_id=str(signal.id), reason=str(exc)
            )
            return None

        if not self._execution_enabled:
            # §12's mandatory dry-run mode - the compensating control for
            # skipping demo-account validation (§0.4). Logs the exact
            # order that would have been placed, computed from the real
            # live account balance, and stops - no `BrokerOrder` row, no
            # bridge call that places anything.
            logger.info(
                "execution.dry_run_order",
                signal_id=str(signal.id),
                symbol=self._execution_symbol,
                direction=signal.signal_type.value,
                volume=str(sizing.volume),
                entry_price=str(signal.entry_price),
                stop_loss=str(signal.stop_loss),
                take_profit=str(signal.take_profit),
                risk_amount=str(sizing.risk_amount),
                account_balance=account.balance,
                account_currency=account.currency,
            )
            return None

        try:
            result = self._provider.place_limit_order(
                symbol=self._execution_symbol,
                direction=signal.signal_type,
                volume=float(sizing.volume),
                open_price=float(signal.entry_price),
                stop_loss=float(signal.stop_loss),
                take_profit=float(signal.take_profit),
            )
        except PermanentExecutionError as exc:
            order = BrokerOrder(
                signal_id=signal.id,
                symbol=self._execution_symbol,
                volume=sizing.volume,
                requested_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                status=OrderStatus.REJECTED,
                rejection_reason=str(exc),
            )
            self._broker_order_repository.create(order)
            self._broker_order_repository.commit()
            logger.warning("execution.order_rejected", signal_id=str(signal.id), reason=str(exc))
            return order
        except TransientExecutionError:
            logger.warning(
                "execution.order_placement_failed", signal_id=str(signal.id), exc_info=True
            )
            return None

        order = BrokerOrder(
            signal_id=signal.id,
            symbol=self._execution_symbol,
            broker_order_id=result.broker_order_id,
            volume=sizing.volume,
            requested_price=Decimal(str(result.requested_price)),
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            status=OrderStatus.PENDING,
        )
        self._broker_order_repository.create(order)
        self._broker_order_repository.commit()
        logger.info(
            "execution.order_placed",
            signal_id=str(signal.id),
            broker_order_id=result.broker_order_id,
            volume=str(sizing.volume),
        )
        return order


__all__ = ["OrderExecutionService"]

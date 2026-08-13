from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.dependencies.execution import get_execution_provider
from app.models.enums import SignalStatus, Timeframe
from app.models.signal import Signal
from app.repositories.broker_order_repository import BrokerOrderRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services.execution.providers.base import OrderExecutionProvider
from app.services.execution.reconciliation_service import reconcile_signal
from app.services.signal.status_resolver import effective_status
from app.services.signal_monitoring_service import entry_touched, evaluate_signal_outcome
from app.workers.celery_app import celery_app

#: Signals span every timeframe (M1-Monthly), but price itself is
#: asset-level, not timeframe-level - the M1 candle (already ingested
#: every minute by `market_data_tasks.py`) is used as the live-price
#: proxy for every active signal on that asset, regardless of the
#: signal's own timeframe.
_PRICE_TIMEFRAME = Timeframe.M1
_MONITORING_INTERVAL_SECONDS = 60.0
#: Matches `signal_tasks.py`'s `asset_repository.list_active(limit=1000)`
#: convention - large enough to cover every active signal in this
#: environment's seeded/demo asset set without unbounded pagination.
_ACTIVE_SIGNAL_LIMIT = 1000


def _monitor_pending_signals(
    signal_repository: SignalRepository,
    candle_repository: PriceCandleRepository,
    broker_order_repository: BrokerOrderRepository,
    session: Session,
    now: datetime,
    execution_provider: OrderExecutionProvider | None,
) -> None:
    """ADR-137: an ACTIVE signal is a pending order, not a live trade -
    it is never evaluated against SL/TP (the production defect this
    phase fixes) until price actually reaches `entry_price`. On that
    same candle, also check SL/TP immediately (§3.3's same-candle
    ambiguity: a gap/spike that both triggers and breaches the stop is
    triggered-then-stopped-out, never left dangling as TRIGGERED).

    A bare TRIGGERED transition (2026-08-07, reverses ADR-137 §3.5's
    original "no message" decision per explicit operator request) sends
    its own Telegram message - `enqueue_signal_triggered_delivery`. A
    same-candle trigger-and-resolve sends only the outcome message, not
    both - the outcome message alone already tells the full story.

    EA Bot spec §6: a signal with a `BrokerOrder` row is reconciled
    against the bridge's real position state (`reconcile_signal`)
    instead of this candle-simulated touch logic - existence of that
    row is the entire fork condition, checked first."""
    signals = signal_repository.find_paginated(
        status=SignalStatus.ACTIVE, limit=_ACTIVE_SIGNAL_LIMIT
    )
    for signal in signals:
        if effective_status(signal.status, signal.created_at, now) != SignalStatus.ACTIVE:
            continue

        broker_order = broker_order_repository.get_by_signal_id(signal.id)
        if broker_order is not None and execution_provider is not None:
            candle = candle_repository.get_latest(signal.asset_id, _PRICE_TIMEFRAME)
            reconcile_signal(
                signal, broker_order, candle, execution_provider, broker_order_repository, now
            )
            continue

        candle = candle_repository.get_latest(signal.asset_id, _PRICE_TIMEFRAME)
        if candle is None or not entry_touched(signal, candle):
            continue

        signal.status = SignalStatus.TRIGGERED
        signal.triggered_at = now

        outcome = evaluate_signal_outcome(signal, candle)
        if outcome is not None:
            signal.status = outcome.status
            signal.closed_at = now
            signal.profit_loss = outcome.profit_loss
        session.commit()

        # Deferred import: avoids a module-level import cycle, mirrors
        # `signal_tasks.py`'s existing best-effort enqueue pattern
        # (docs/57 §5) - a broker outage must not stop the rest of
        # this run or block the next signal's evaluation.
        if outcome is not None:
            from app.workers.telegram_tasks import enqueue_signal_outcome_delivery

            enqueue_signal_outcome_delivery(str(signal.id))
        else:
            from app.workers.telegram_tasks import enqueue_signal_triggered_delivery

            enqueue_signal_triggered_delivery(str(signal.id))


def _monitor_triggered_signals(
    signal_repository: SignalRepository,
    candle_repository: PriceCandleRepository,
    broker_order_repository: BrokerOrderRepository,
    session: Session,
    now: datetime,
    execution_provider: OrderExecutionProvider | None,
) -> None:
    """ADR-137: SL/TP are only ever evaluated for a `TRIGGERED` (live)
    signal. A signal past `signal_triggered_ttl_hours` since
    `triggered_at` is already effectively CLOSED read-time-only
    (`status_resolver.effective_status`, same treatment as EXPIRED) -
    nothing to persist, just skip it.

    EA Bot spec §6: same reconciliation fork as
    `_monitor_pending_signals` - a `BrokerOrder`-backed signal's close
    detection is driven by the bridge's real position state, not this
    candle-simulated SL/TP check."""
    signals: list[Signal] = list(
        signal_repository.find_paginated(status=SignalStatus.TRIGGERED, limit=_ACTIVE_SIGNAL_LIMIT)
    )
    for signal in signals:
        current = effective_status(
            signal.status, signal.created_at, now, triggered_at=signal.triggered_at
        )
        if current != SignalStatus.TRIGGERED:
            continue

        broker_order = broker_order_repository.get_by_signal_id(signal.id)
        if broker_order is not None and execution_provider is not None:
            candle = candle_repository.get_latest(signal.asset_id, _PRICE_TIMEFRAME)
            reconcile_signal(
                signal, broker_order, candle, execution_provider, broker_order_repository, now
            )
            continue

        candle = candle_repository.get_latest(signal.asset_id, _PRICE_TIMEFRAME)
        if candle is None:
            continue

        outcome = evaluate_signal_outcome(signal, candle)
        if outcome is None:
            continue

        signal.status = outcome.status
        signal.closed_at = now
        signal.profit_loss = outcome.profit_loss
        session.commit()

        from app.workers.telegram_tasks import enqueue_signal_outcome_delivery

        enqueue_signal_outcome_delivery(str(signal.id))


@celery_app.task(name="signals.monitor_active")  # type: ignore[untyped-decorator]
def monitor_active_signals_task() -> None:
    """Checks every pending (ACTIVE) signal for entry-trigger and every
    live (TRIGGERED) signal's price against its Stop Loss/Take Profit on
    each tick (docs/51 §10's deferred "live price-monitoring,
    trigger-detection, and outcome tracking", completed by ADR-137). The
    first code path to mutate `Signal.status` after creation
    (ADR-088/091 - previously write-once)."""
    session = SessionLocal()
    try:
        signal_repository = SignalRepository(session)
        candle_repository = PriceCandleRepository(session)
        broker_order_repository = BrokerOrderRepository(session)
        now = datetime.now(UTC)

        # Only build a real bridge connection if at least one
        # `BrokerOrder` exists at all (EA Bot spec §6) - avoids an
        # unnecessary MetaApi connection attempt on every 60s tick in
        # every environment that has never executed a real order.
        execution_provider = (
            get_execution_provider() if broker_order_repository.count_filtered() > 0 else None
        )

        _monitor_pending_signals(
            signal_repository,
            candle_repository,
            broker_order_repository,
            session,
            now,
            execution_provider,
        )
        _monitor_triggered_signals(
            signal_repository,
            candle_repository,
            broker_order_repository,
            session,
            now,
            execution_provider,
        )
    finally:
        session.close()


def register_signal_monitoring_schedule() -> dict[str, dict[str, object]]:
    """Celery Beat schedule entry - mirrors
    `market_data_tasks.register_market_data_schedule`'s shape."""
    return {
        "signals-monitor-active": {
            "task": "signals.monitor_active",
            "schedule": _MONITORING_INTERVAL_SECONDS,
        }
    }

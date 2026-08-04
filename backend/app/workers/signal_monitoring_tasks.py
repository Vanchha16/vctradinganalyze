from datetime import UTC, datetime

from app.database.session import SessionLocal
from app.models.enums import SignalStatus, Timeframe
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services.signal.status_resolver import effective_status
from app.services.signal_monitoring_service import evaluate_signal_outcome
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


@celery_app.task(name="signals.monitor_active")  # type: ignore[untyped-decorator]
def monitor_active_signals_task() -> None:
    """Checks every ACTIVE signal's price against its Stop Loss/Take
    Profit on each tick (docs/51 §10's deferred "live price-monitoring,
    trigger-detection, and outcome tracking"). The first code path to
    mutate `Signal.status` after creation (ADR-088/091 - previously
    write-once)."""
    session = SessionLocal()
    try:
        signal_repository = SignalRepository(session)
        candle_repository = PriceCandleRepository(session)
        now = datetime.now(UTC)

        signals = signal_repository.find_paginated(
            status=SignalStatus.ACTIVE, limit=_ACTIVE_SIGNAL_LIMIT
        )
        for signal in signals:
            if effective_status(signal.status, signal.created_at, now) != SignalStatus.ACTIVE:
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

            # Deferred import: avoids a module-level import cycle, mirrors
            # `signal_tasks.py`'s existing best-effort enqueue pattern
            # (docs/57 §5) - a broker outage must not stop the rest of
            # this run or block the next signal's evaluation.
            from app.workers.telegram_tasks import enqueue_signal_outcome_delivery

            enqueue_signal_outcome_delivery(str(signal.id))
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

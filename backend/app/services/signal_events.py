"""Publishes signal lifecycle events to the `signals:updates` Redis
channel - the single place that builds these payloads, so
`routes/signals.py` and `signal_monitoring_tasks.py` (two call sites for
`status_changed` alone) can't drift out of sync with each other the way
three independent copies of the same dict literal would.
"""

from app.core.redis_pubsub import get_signal_channel, publish_event_sync
from app.models.signal import Signal


def publish_signal_created(signal: Signal, symbol: str) -> None:
    """Fail-open: a Redis outage must never fail signal generation."""
    try:
        publish_event_sync(
            get_signal_channel(),
            {
                "event": "created",
                "signal_id": str(signal.id),
                "symbol": symbol,
                "signal_type": signal.signal_type.value,
                "status": signal.status.value,
                "entry_price": float(signal.entry_price),
                "stop_loss": float(signal.stop_loss),
                "take_profit": float(signal.take_profit),
                "confidence": float(signal.confidence) if signal.confidence else None,
                "created_at": signal.created_at.isoformat() if signal.created_at else None,
            },
        )
    except Exception:
        pass


def publish_signal_status_changed(signal: Signal) -> None:
    """Fail-open: a Redis outage must never fail signal monitoring."""
    try:
        publish_event_sync(
            get_signal_channel(),
            {
                "event": "status_changed",
                "signal_id": str(signal.id),
                "asset_id": str(signal.asset_id),
                "status": signal.status.value,
                "profit_loss": (
                    float(signal.profit_loss) if signal.profit_loss is not None else None
                ),
                "closed_at": signal.closed_at.isoformat() if signal.closed_at else None,
                "triggered_at": (
                    signal.triggered_at.isoformat() if signal.triggered_at else None
                ),
            },
        )
    except Exception:
        pass

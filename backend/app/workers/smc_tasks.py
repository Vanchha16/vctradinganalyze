"""ADR-183 - the smc-ict-crt-v1 production loop.

Runs every five minutes, on XAUUSD only, and reads the database alone: it
adds **no** market-data provider requests, so the Twelve Data budget is
unchanged. A disabled run returns immediately, having touched nothing.

Deliberately separate from `signal_tasks.py`: SMC does not pass through the
strategy scorer, the risk engine, the AI orchestrator or the M1 confirmation
task, and BBMA's path is not touched by anything here.
"""

import uuid
from datetime import UTC, datetime

import structlog
from celery.schedules import crontab

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.telegram import get_telegram_provider
from app.models.signal import Signal
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services.smc_crt.service import SmcCrtService
from app.services.telegram.message_sections import escape_markdown_v2
from app.services.telegram_service import TelegramService
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

#: XAUUSD only (the operator's scope). Not `list_active()`: activating
#: another asset must never silently start trading it with this strategy.
SYMBOL = "XAUUSD"


@celery_app.task(name="smc.run")  # type: ignore[untyped-decorator]
def run_smc_task() -> None:
    if not settings.smc_enabled:
        return
    created: list[uuid.UUID] = []
    rejected: list[uuid.UUID] = []
    session = SessionLocal()
    try:
        assets = AssetRepository(session)
        asset = assets.get_by_symbol(SYMBOL)
        if asset is None or not asset.is_active:
            logger.warning("smc.asset_unavailable", symbol=SYMBOL)
            return
        service = SmcCrtService(
            SmcSetupRepository(session),
            PriceCandleRepository(session),
            SignalRepository(session),
            AIAnalysisRepository(session),
            AuditLogRepository(session),
        )
        touched = service.run(asset, datetime.now(UTC))
        session.commit()
        created, rejected = service.created_signals, service.execution_rejections
        if touched:
            logger.info(
                "smc.run_complete",
                setups=[{"anchor": s.anchor_t.isoformat(), "state": str(s.state),
                         "reason": s.reason} for s in touched],
            )
    except Exception:
        session.rollback()
        logger.exception("smc.run_failed")
        raise
    finally:
        session.close()

    # Audit D1. Only now that the commit has succeeded: a delivery task must
    # be able to read the row, and a rolled-back run must deliver nothing.
    # Exactly once per signal - a setup that reached SIGNAL_CREATED is never
    # re-evaluated, so a later or retried run never lists it again.
    _deliver(created, rejected)


def _deliver(created: list[uuid.UUID], rejected: list[uuid.UUID]) -> None:
    """Best-effort Telegram hand-off, the same as every other signal path
    (docs/57 §5): a broker outage is logged and never undoes a signal that is
    already committed and already visible to the EA."""
    from app.workers.telegram_tasks import enqueue_signal_delivery

    for signal_id in created:
        try:
            enqueue_signal_delivery(str(signal_id))
        except Exception:  # noqa: BLE001 - never fail the run over a notification
            logger.exception("smc.telegram_enqueue_failed", signal_id=str(signal_id))
    for signal_id in rejected:
        try:
            notify_execution_rejected_task.delay(str(signal_id))
        except Exception:  # noqa: BLE001
            logger.exception("smc.rejection_notice_failed", signal_id=str(signal_id))


@celery_app.task(name="smc.notify_execution_rejected", ignore_result=True)  # type: ignore[untyped-decorator]
def notify_execution_rejected_task(signal_id: str) -> None:
    """Audit D3: tell the operator a signal was refused at execution - in
    plain words, so it is never read as a trade that stopped out. Operators
    only: nobody else has anything to act on."""
    session = SessionLocal()
    try:
        signal = SignalRepository(session).get_by_id(uuid.UUID(signal_id))
        if signal is None:
            return
        service = TelegramService(
            account_repository=TelegramAccountRepository(session),
            provider=get_telegram_provider(),
        )
        service.send_to_operators(compose_execution_rejected_message(signal))
    finally:
        session.close()


def compose_execution_rejected_message(signal: Signal) -> str:
    lines = [
        "⚠️ SMC-ICT-CRT v1 signal REJECTED BY EXECUTION SAFETY",
        "No order was sent to the broker. This is not a trade and not a loss.",
        "",
        f"Direction : {signal.signal_type.value.upper()} XAUUSD",
        f"Entry : {signal.entry_price:.3f}",
        f"Stop loss : {signal.stop_loss:.3f}",
        f"Take profit : {signal.take_profit:.3f}",
        f"Reason : {signal.status_reason or ''}",
        f"Signal : {signal.id}",
    ]
    return "\n".join(escape_markdown_v2(line) for line in lines)


def register_smc_schedule() -> dict[str, dict[str, object]]:
    """Every five minutes, on the minute after each M5 collection."""
    return {"smc-run": {"task": "smc.run", "schedule": crontab(minute="*/5")}}

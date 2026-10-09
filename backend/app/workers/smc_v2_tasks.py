"""ADR-185 - the smc-ict-crt-v2 design-A production loop.

Every five minutes, XAUUSD only, database reads only: **no** market-data
provider requests, so the Twelve Data budget is unchanged. A disabled run
returns immediately, having touched nothing.

v2 replaces v1's signal generation; the two never publish together. While
`smc_enabled` (v1) is on, this task does nothing and says so - the
switch-over is: v1 off first, then v2 on (ADR-185, activation steps).
"""

import uuid
from datetime import UTC, datetime

import structlog
from celery.schedules import crontab

from app.config import settings
from app.database.session import SessionLocal
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_v2_setup_repository import SmcV2SetupRepository
from app.services.smc_crt_v2.service import SmcCrtV2Service
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

#: XAUUSD only (the operator's scope). Not `list_active()`: activating
#: another asset must never silently start trading it with this strategy.
SYMBOL = "XAUUSD"


@celery_app.task(name="smc_v2.run")  # type: ignore[untyped-decorator]
def run_smc_v2_task() -> None:
    if not settings.smc_v2_enabled:
        return
    if settings.smc_enabled:
        logger.warning("smc_v2.blocked_while_v1_enabled")
        return
    created: list[uuid.UUID] = []
    session = SessionLocal()
    try:
        asset = AssetRepository(session).get_by_symbol(SYMBOL)
        if asset is None or not asset.is_active:
            logger.warning("smc_v2.asset_unavailable", symbol=SYMBOL)
            return
        service = SmcCrtV2Service(
            SmcV2SetupRepository(session),
            PriceCandleRepository(session),
            SignalRepository(session),
            AIAnalysisRepository(session),
            AuditLogRepository(session),
        )
        touched = service.run(asset, datetime.now(UTC))
        session.commit()
        created = service.created_signals
        if touched:
            logger.info(
                "smc_v2.run_complete",
                setups=[{"anchor": s.anchor_t.isoformat(), "state": str(s.state),
                         "reason": s.reason} for s in touched],
            )
    except Exception:
        session.rollback()
        logger.exception("smc_v2.run_failed")
        raise
    finally:
        session.close()

    # Only once the commit has succeeded (as v1, audit D1): a rolled-back run
    # delivers nothing, and a published setup is never re-evaluated, so each
    # signal is handed to Telegram exactly once.
    _deliver(created)


def _deliver(created: list[uuid.UUID]) -> None:
    from app.workers.telegram_tasks import enqueue_signal_delivery

    for signal_id in created:
        try:
            enqueue_signal_delivery(str(signal_id))
        except Exception:  # noqa: BLE001 - never fail the run over a notification
            logger.exception("smc_v2.telegram_enqueue_failed", signal_id=str(signal_id))


def register_smc_v2_schedule() -> dict[str, dict[str, object]]:
    """Every five minutes at minute 4, like v1: M5 is collected at minute 3
    after its close (audit D9), so this is the first run to see it final."""
    return {"smc-v2-run": {"task": "smc_v2.run", "schedule": crontab(minute="4-59/5")}}

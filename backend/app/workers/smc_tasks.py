"""ADR-183 - the smc-ict-crt-v1 production loop.

Runs every five minutes, on XAUUSD only, and reads the database alone: it
adds **no** market-data provider requests, so the Twelve Data budget is
unchanged. A disabled run returns immediately, having touched nothing.

Deliberately separate from `signal_tasks.py`: SMC does not pass through the
strategy scorer, the risk engine, the AI orchestrator or the M1 confirmation
task, and BBMA's path is not touched by anything here.
"""

from datetime import UTC, datetime

import structlog
from celery.schedules import crontab

from app.config import settings
from app.database.session import SessionLocal
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.services.smc_crt.service import SmcCrtService
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

#: XAUUSD only (the operator's scope). Not `list_active()`: activating
#: another asset must never silently start trading it with this strategy.
SYMBOL = "XAUUSD"


@celery_app.task(name="smc.run")  # type: ignore[untyped-decorator]
def run_smc_task() -> None:
    if not settings.smc_enabled:
        return
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
        )
        touched = service.run(asset, datetime.now(UTC))
        session.commit()
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


def register_smc_schedule() -> dict[str, dict[str, object]]:
    """Every five minutes, on the minute after each M5 collection."""
    return {"smc-run": {"task": "smc.run", "schedule": crontab(minute="*/5")}}

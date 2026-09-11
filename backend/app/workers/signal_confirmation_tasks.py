"""Confirms or cancels DRAFT signals after each M15 close (ADR-166).

Rules-only - no AI call. A confirmed draft becomes ACTIVE and is published
here, not at creation: this is the only place a website "created" event
and the Telegram message go out for a signal that waited for confirmation.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from celery.schedules import crontab
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.dependencies.smc import get_smc_engine
from app.exceptions import ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import SignalStatus, Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services import signal_confirmation_service
from app.services.signal_confirmation_service import ConfirmationOutcome
from app.services.smc.types import SMCAnalysisResult
from app.services.smc_engine import SMCEngine
from app.utils.time import as_aware_utc
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

_PRICE_TIMEFRAME = Timeframe.M1
_CONFIRMATION_TIMEFRAME = Timeframe.M15
#: Two minutes after each M15 collection (minutes 1, 16, 31, 46 -
#: `market_data_tasks`), so every run reads the candle that just closed.
_SCHEDULE = crontab(minute="3,18,33,48")
_DRAFT_LIMIT = 1000


def _m15_structure(smc_engine: SMCEngine, asset: Asset) -> SMCAnalysisResult | None:
    try:
        return smc_engine.analyze(asset, _CONFIRMATION_TIMEFRAME)
    except ResourceNotFoundException:
        return None


def confirm_pending_signals(
    signal_repository: SignalRepository,
    candle_repository: PriceCandleRepository,
    asset_repository: AssetRepository,
    smc_engine: SMCEngine,
    session: Session,
    now: datetime,
) -> None:
    drafts = signal_repository.find_paginated(status=SignalStatus.DRAFT, limit=_DRAFT_LIMIT)
    # One M15 analysis per asset per run, however many drafts it has.
    structure: dict[UUID, SMCAnalysisResult | None] = {}

    for signal in drafts:
        asset = asset_repository.get_by_id(signal.asset_id)
        if asset is None:
            continue
        if asset.id not in structure:
            structure[asset.id] = _m15_structure(smc_engine, asset)

        candles = list(
            candle_repository.list_range(
                signal.asset_id,
                _PRICE_TIMEFRAME,
                start=as_aware_utc(signal.created_at),
                end=now,
            )
        )
        decision = signal_confirmation_service.evaluate(signal, candles, structure[asset.id], now)
        if decision.outcome is ConfirmationOutcome.PENDING:
            continue

        signal.status_reason = decision.reason

        if decision.outcome is ConfirmationOutcome.CANCELLED:
            signal.status = SignalStatus.CANCELLED
            session.commit()
            logger.info("signals.draft_cancelled", signal_id=str(signal.id), reason=decision.reason)

            from app.services.signal_events import publish_signal_status_changed

            publish_signal_status_changed(signal)
            continue

        signal.status = SignalStatus.ACTIVE
        signal.confirmed_at = now
        # The monitor looks for the entry touch from here on, not from
        # `created_at`: price touching entry while this was still a draft was
        # not a fill anyone could have had - nobody had been sent the signal.
        signal.last_monitored_at = now
        session.commit()
        logger.info("signals.draft_confirmed", signal_id=str(signal.id), reason=decision.reason)

        # Deferred imports, same reason as `signal_tasks.py`: avoids a
        # module-level import cycle through `celery_app`.
        from app.services.signal_events import publish_signal_created
        from app.workers.telegram_tasks import enqueue_signal_delivery

        publish_signal_created(signal, asset.symbol)
        enqueue_signal_delivery(str(signal.id))


@celery_app.task(name="signals.confirm_pending")  # type: ignore[untyped-decorator]
def confirm_pending_signals_task() -> None:
    session = SessionLocal()
    try:
        confirm_pending_signals(
            SignalRepository(session),
            PriceCandleRepository(session),
            AssetRepository(session),
            get_smc_engine(session),
            session,
            datetime.now(UTC),
        )
    finally:
        session.close()


def register_signal_confirmation_schedule() -> dict[str, dict[str, object]]:
    return {
        "signals-confirm-pending": {
            "task": "signals.confirm_pending",
            "schedule": _SCHEDULE,
        }
    }

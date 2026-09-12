"""Confirms or cancels DRAFT signals after each M15 close (ADR-166).

Rules-only - no AI call. A confirmed draft becomes ACTIVE and is published
here, not at creation: this is the only place a website "created" event
and the Telegram message go out for a signal that waited for confirmation.

ADR-168: a confirmed draft also replaces an older signal for the same asset
and timeframe that has not filled. The replaced signal leaves the EA feed,
which is the EA's cue to delete its pending order.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from celery.schedules import crontab
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.smc import get_smc_engine
from app.exceptions import ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import SignalStatus, Timeframe
from app.models.signal import Signal
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services import signal_confirmation_service
from app.services.signal.status_resolver import effective_status
from app.services.signal_confirmation_service import (
    REPLACED_REASON,
    SAME_SETUP_REASON,
    TRADE_LIVE_REASON,
    ConfirmationOutcome,
)
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
_OPEN_STATUSES = frozenset({SignalStatus.ACTIVE, SignalStatus.TRIGGERED})


def _m15_structure(smc_engine: SMCEngine, asset: Asset) -> SMCAnalysisResult | None:
    try:
        return smc_engine.analyze(asset, _CONFIRMATION_TIMEFRAME)
    except ResourceNotFoundException:
        return None


def _open_signals(
    signal_repository: SignalRepository, draft: Signal, now: datetime
) -> list[tuple[Signal, SignalStatus]]:
    """Signals already out for the draft's asset and timeframe, with their
    read-time status: ACTIVE (no fill yet) or TRIGGERED (a live trade). An
    ACTIVE row past its TTL is expired, not open (ADR-088/137)."""
    lookback = timedelta(hours=settings.signal_ttl_hours + settings.signal_triggered_ttl_hours)
    open_signals: list[tuple[Signal, SignalStatus]] = []
    for other in signal_repository.find_open_for_asset(
        draft.asset_id, created_since=now - lookback
    ):
        if other.id == draft.id or other.timeframe != draft.timeframe:
            continue
        status = effective_status(
            other.status, other.created_at, now, triggered_at=other.triggered_at
        )
        if status in _OPEN_STATUSES:
            open_signals.append((other, status))
    return open_signals


def _cancel_draft(signal: Signal, reason: str | None, session: Session) -> None:
    """Cancelled with its reason, and the website told - but no Telegram
    message: nobody was ever told about the draft."""
    signal.status = SignalStatus.CANCELLED
    signal.status_reason = reason
    session.commit()
    logger.info("signals.draft_cancelled", signal_id=str(signal.id), reason=reason)

    from app.services.signal_events import publish_signal_status_changed

    publish_signal_status_changed(signal)


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

        open_signals = _open_signals(signal_repository, signal, now)
        # ADR-168: the hourly job keeps analysing while a signal is unfilled,
        # so it finds that signal's setup again. Cancel the repeat at once
        # rather than let it wait for M15 and republish the same trade.
        if any(
            status is SignalStatus.ACTIVE
            and signal_confirmation_service.is_same_setup(signal, other)
            for other, status in open_signals
        ):
            _cancel_draft(signal, SAME_SETUP_REASON, session)
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

        if decision.outcome is ConfirmationOutcome.CANCELLED:
            _cancel_draft(signal, decision.reason, session)
            continue

        # ADR-168: a live trade is never replaced. The earlier signal filled
        # while this draft waited, so this one does not go out.
        if any(status is SignalStatus.TRIGGERED for _, status in open_signals):
            _cancel_draft(signal, TRADE_LIVE_REASON, session)
            continue

        replaced = [other for other, status in open_signals if status is SignalStatus.ACTIVE]
        for other in replaced:
            other.status = SignalStatus.CANCELLED
            other.status_reason = REPLACED_REASON

        signal.status = SignalStatus.ACTIVE
        signal.status_reason = decision.reason
        signal.confirmed_at = now
        # The monitor looks for the entry touch from here on, not from
        # `created_at`: price touching entry while this was still a draft was
        # not a fill anyone could have had - nobody had been sent the signal.
        signal.last_monitored_at = now
        session.commit()
        logger.info(
            "signals.draft_confirmed",
            signal_id=str(signal.id),
            reason=decision.reason,
            replaced=[str(other.id) for other in replaced],
        )

        # Deferred imports, same reason as `signal_tasks.py`: avoids a
        # module-level import cycle through `celery_app`.
        from app.services.signal_events import publish_signal_created, publish_signal_status_changed
        from app.workers.telegram_tasks import (
            enqueue_signal_cancelled_delivery,
            enqueue_signal_delivery,
        )

        for other in replaced:
            publish_signal_status_changed(other)
            enqueue_signal_cancelled_delivery(str(other.id))
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

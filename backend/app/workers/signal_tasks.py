import uuid
from datetime import UTC, datetime

from app.database.session import SessionLocal
from app.dependencies.ai_orchestrator import (
    get_ai_analysis_repository,
    get_ai_orchestrator_engine,
    get_ai_provider,
    get_context_builder,
)
from app.dependencies.analysis_confidence import get_analysis_confidence_engine
from app.dependencies.economic_calendar import get_economic_calendar_engine
from app.dependencies.market_regime import get_market_regime_engine
from app.dependencies.news import get_news_sentiment_engine
from app.dependencies.risk_management import get_risk_management_engine
from app.dependencies.signal import get_signal_engine
from app.dependencies.smc import get_smc_engine
from app.dependencies.strategy import get_strategy_engine
from app.dependencies.technical_analysis import get_technical_analysis_engine
from app.models.enums import SignalStatus, Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.economic_event_repository import EconomicEventRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services.signal.status_resolver import effective_status
from app.workers.celery_app import celery_app

#: Automatic generation runs against the seeded/active asset set only
#: (confirmed scope: "seeded watchlist assets only, hourly") - the same
#: `AssetRepository.list_active()` call `market_data_tasks.py` already
#: uses, which in this environment *is* the seeded demo set (no separate
#: Watchlist backend feature exists yet, ADR-103). One evaluation per
#: asset per run, on H1 only - not every timeframe - to keep OpenAI/
#: market-data usage predictable at this cadence.
_TIMEFRAME = Timeframe.H1
_SIGNAL_GENERATION_INTERVAL_SECONDS = 3600.0


def _has_open_signal(
    signal_repository: SignalRepository, asset_id: uuid.UUID, now: datetime
) -> bool:
    """True if this asset already has a BUY/SELL call on `_TIMEFRAME`
    that hasn't expired/closed yet (ADR-088/ADR-137's `effective_status`,
    same check `signal_monitoring_tasks.py` uses) - the hourly job's
    confirmation gate: don't re-signal an asset that already has an
    open, unresolved call outstanding.

    ADR-137: a `TRIGGERED` signal is a *live trade*, more open than a
    pending `ACTIVE` one - it must also block regeneration, or the new
    state would silently reopen ADR-125's dedup gate the moment a
    pending order fills."""
    active = signal_repository.find_paginated(
        asset_id=asset_id,
        timeframe=_TIMEFRAME,
        status=SignalStatus.ACTIVE,
        limit=1,
    )
    if any(
        effective_status(signal.status, signal.created_at, now) == SignalStatus.ACTIVE
        for signal in active
    ):
        return True

    triggered = signal_repository.find_paginated(
        asset_id=asset_id,
        timeframe=_TIMEFRAME,
        status=SignalStatus.TRIGGERED,
        limit=1,
    )
    return any(
        effective_status(
            signal.status, signal.created_at, now, triggered_at=signal.triggered_at
        )
        == SignalStatus.TRIGGERED
        for signal in triggered
    )


@celery_app.task(name="signals.generate_for_watchlist")  # type: ignore[untyped-decorator]
def generate_signals_task() -> None:
    """Hourly automatic signal generation (docs/51 §6 extended to a
    scheduled trigger). Calls the exact same `SignalEngine.generate()`
    path `POST /signals/generate/{symbol}` already uses - zero new
    decision/scoring logic, only a new trigger. Builds the same
    dependency graph FastAPI would per-request by calling the existing
    `app.dependencies.*` composition functions directly (mirrors
    `market_data_tasks.py`'s manual-construction convention for
    Celery tasks, which have no request-scoped `Depends` resolution).
    """
    session = SessionLocal()
    try:
        technical_analysis_engine = get_technical_analysis_engine(session)
        smc_engine = get_smc_engine(session)
        market_regime_engine = get_market_regime_engine(
            session, technical_analysis_engine, smc_engine
        )
        confidence_engine = get_analysis_confidence_engine(
            technical_analysis_engine, smc_engine, market_regime_engine
        )
        news_sentiment_engine = get_news_sentiment_engine(NewsSentimentRepository(session))
        economic_calendar_engine = get_economic_calendar_engine(EconomicEventRepository(session))
        price_candle_repository = PriceCandleRepository(session)
        asset_repository = AssetRepository(session)

        strategy_engine = get_strategy_engine(
            confidence_engine, economic_calendar_engine, price_candle_repository
        )
        risk_management_engine = get_risk_management_engine(
            confidence_engine,
            news_sentiment_engine,
            economic_calendar_engine,
            price_candle_repository,
            asset_repository,
        )
        context_builder = get_context_builder(
            confidence_engine,
            news_sentiment_engine,
            economic_calendar_engine,
            strategy_engine,
            risk_management_engine,
        )
        ai_orchestrator_engine = get_ai_orchestrator_engine(
            context_builder,
            get_ai_provider(),
            get_ai_analysis_repository(session),
        )
        signal_repository = SignalRepository(session)
        signal_engine = get_signal_engine(ai_orchestrator_engine, signal_repository)

        # `SignalEngine.generate()` already commits internally (via
        # `SignalRepository.commit()`, same as `AIOrchestratorEngine`) -
        # no extra commit needed here, unlike `market_data_tasks.py`'s
        # `MarketDataService.collect()`, which doesn't self-commit.
        now = datetime.now(UTC)
        for asset in asset_repository.list_active(limit=1000):
            if _has_open_signal(signal_repository, asset.id, now):
                # An unresolved BUY/SELL call already exists for this
                # asset/timeframe (ADR-088 EXPIRED is read-time-only, so
                # this re-checks effective_status rather than trusting
                # the stored ACTIVE status). Re-running the full AI
                # orchestration hourly would only ever re-confirm or
                # contradict that same open call, spamming Telegram with
                # near-duplicate signals (docs/57 §8's deferred
                # "deduplication" gap) - skip until it closes/expires.
                continue

            result = signal_engine.generate(asset, _TIMEFRAME)
            if result.signal is not None:
                # Deferred import: avoids a module-level import cycle
                # (telegram_tasks -> celery_app -> workers/__init__ ->
                # this module), mirrors how Celery task modules already
                # only import `celery_app` back, never each other, at
                # module scope. Best-effort enqueue (docs/57 §5) - a
                # broker outage must not stop the rest of this run.
                from app.workers.telegram_tasks import enqueue_signal_delivery

                enqueue_signal_delivery(str(result.signal.id))
    finally:
        session.close()


def register_signal_schedule() -> dict[str, dict[str, object]]:
    """Celery Beat schedule entry - mirrors
    `market_data_tasks.register_market_data_schedule`'s shape."""
    return {
        "generate-signals-watchlist": {
            "task": "signals.generate_for_watchlist",
            "schedule": _SIGNAL_GENERATION_INTERVAL_SECONDS,
        }
    }

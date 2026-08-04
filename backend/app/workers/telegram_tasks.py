import uuid

import structlog

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.telegram import get_telegram_provider
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.system_setting_repository import SystemSettingRepository
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services.telegram_service import TelegramService, escape_markdown_v2
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

_OFFSET_SETTING_KEY = "telegram_last_update_id"


@celery_app.task(name="telegram.poll_updates")  # type: ignore[untyped-decorator]
def poll_updates_task() -> None:
    """Long-polls `getUpdates` and resolves `/start <link_code>` commands
    (docs/57 §3/§7) - a Celery Beat task, not a public webhook (ADR-112).
    Silently no-ops if Telegram isn't configured yet."""
    if not settings.telegram_bot_token:
        return

    session = SessionLocal()
    try:
        provider = get_telegram_provider()
        settings_repository = SystemSettingRepository(session)
        telegram_service = TelegramService(
            account_repository=TelegramAccountRepository(session), provider=provider
        )

        stored_offset = settings_repository.get_by_key(_OFFSET_SETTING_KEY)
        offset = int(stored_offset.value) if stored_offset is not None else None

        updates = provider.get_updates(offset)
        if not updates:
            return

        for update in updates:
            if update.text and update.text.startswith("/start "):
                code = update.text.removeprefix("/start ").strip()
                account = telegram_service.resolve_link_code(code, update.chat_id)
                reply = (
                    "Linked to ClaudeTrading AI. You'll receive trading signals here."
                    if account is not None
                    else "That link code is invalid or expired. Generate a new one from Settings."
                )
                provider.send_message(update.chat_id, escape_markdown_v2(reply))

        settings_repository.upsert(_OFFSET_SETTING_KEY, str(max(u.update_id for u in updates) + 1))
        session.commit()
    finally:
        session.close()


@celery_app.task(name="telegram.send_signal", ignore_result=True)  # type: ignore[untyped-decorator]
def send_signal_telegram_task(signal_id: str) -> None:
    """Delivery hook (docs/57 §5) called after `SignalEngine.generate()`
    persists a BUY/SELL `Signal` - from both the on-demand
    `POST /signals/generate/{symbol}` route and the automatic
    `signals.generate_for_watchlist` task."""
    session = SessionLocal()
    try:
        signal_repository = SignalRepository(session)
        signal = signal_repository.get_by_id(uuid.UUID(signal_id))
        if signal is None:
            return

        analysis = AIAnalysisRepository(session).get_by_id(signal.analysis_id)
        asset = AssetRepository(session).get_by_id(signal.asset_id)
        if analysis is None or asset is None:
            return

        telegram_service = TelegramService(
            account_repository=TelegramAccountRepository(session),
            provider=get_telegram_provider(),
        )
        telegram_service.send_signal(signal, analysis, asset)
    finally:
        session.close()


def enqueue_signal_delivery(signal_id: str) -> None:
    """Best-effort enqueue of `send_signal_telegram_task` (docs/57 §5).

    Telegram delivery is a notification, not the operation the caller
    actually requested (generating/persisting a `Signal`, which has
    already succeeded by the time this is called) - a broker outage here
    must never fail or roll back that already-completed work. Mirrors
    docs/20 §10's "log and move on" failure handling, applied at the
    enqueue step rather than only at delivery time.
    """
    try:
        send_signal_telegram_task.delay(signal_id)
    except Exception:
        logger.warning(
            "telegram_signal_delivery_enqueue_failed", signal_id=signal_id, exc_info=True
        )


def register_telegram_schedule() -> dict[str, dict[str, object]]:
    """Celery Beat schedule entry - mirrors
    `market_data_tasks.register_market_data_schedule`'s shape."""
    return {
        "telegram-poll-updates": {
            "task": "telegram.poll_updates",
            "schedule": float(settings.telegram_poll_interval_seconds),
        }
    }

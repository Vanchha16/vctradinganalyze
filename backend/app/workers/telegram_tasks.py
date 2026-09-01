import uuid

import structlog
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.telegram import get_telegram_provider
from app.models.enums import Timeframe
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.system_setting_repository import SystemSettingRepository
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services.telegram.chart_renderer import (
    format_current_price_caption,
    render_candlestick_chart,
)
from app.services.telegram.conversation_state import (
    consume_awaiting_chart_symbol,
    mark_awaiting_chart_symbol,
)
from app.services.telegram.keyboards import (
    CALLBACK_SHOW_CHART,
    CALLBACK_SUMMARY_REPORT,
    build_main_menu_keyboard,
)
from app.services.telegram.providers.base import RawTelegramUpdate, TelegramProvider
from app.services.telegram.report_builder import build_summary_report_text
from app.services.telegram_service import TelegramService, escape_markdown_v2
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

_OFFSET_SETTING_KEY = "telegram_last_update_id"
#: Menu commands (§13) - `/start` bare (no link code) is included so a
#: user who already linked and just types `/start` again sees the menu
#: instead of the link-code error path below.
_MENU_COMMANDS = {"/start", "/menu", "/help"}
_CHART_CANDLE_LIMIT = 60
_UNLINKED_ACCOUNT_MESSAGE = (
    "Link your account first: generate a code from Settings, then send /start <code> here."
)


@celery_app.task(name="telegram.poll_updates")  # type: ignore[untyped-decorator]
def poll_updates_task() -> None:
    """Long-polls `getUpdates` and handles every interaction the bot
    supports (docs/57 §3/§7, extended by §13's menu buttons) - a Celery
    Beat task, not a public webhook (ADR-112). Silently no-ops if
    Telegram isn't configured yet."""
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
            _handle_update(update, session, provider, telegram_service)

        settings_repository.upsert(_OFFSET_SETTING_KEY, str(max(u.update_id for u in updates) + 1))
        session.commit()
    finally:
        session.close()


def _handle_update(
    update: RawTelegramUpdate,
    session: Session,
    provider: TelegramProvider,
    telegram_service: TelegramService,
) -> None:
    if update.callback_query_id is not None:
        _handle_callback_query(update, provider, telegram_service, session)
        return

    if update.text and update.text.startswith("/start ") and len(update.text.split()) > 1:
        code = update.text.removeprefix("/start ").strip()
        account = telegram_service.resolve_link_code(code, update.chat_id)
        reply = (
            "Linked to ClaudeTrading AI. You'll receive trading signals here."
            if account is not None
            else "That link code is invalid or expired. Generate a new one from Settings."
        )
        provider.send_message(update.chat_id, escape_markdown_v2(reply))
        if account is not None:
            provider.send_message(
                update.chat_id,
                escape_markdown_v2("What would you like to do?"),
                reply_markup=build_main_menu_keyboard(),
            )
        return

    if update.text and update.text.strip() in _MENU_COMMANDS:
        provider.send_message(
            update.chat_id,
            escape_markdown_v2("What would you like to do?"),
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if update.text and not update.text.startswith("/"):
        _handle_possible_symbol_reply(update, session, provider)


def _handle_callback_query(
    update: RawTelegramUpdate,
    provider: TelegramProvider,
    telegram_service: TelegramService,
    session: Session,
) -> None:
    assert update.callback_query_id is not None
    try:
        provider.answer_callback_query(update.callback_query_id)
    except Exception:
        logger.warning("telegram.answer_callback_query_failed", exc_info=True)

    if not telegram_service.is_linked_chat(update.chat_id):
        provider.send_message(update.chat_id, escape_markdown_v2(_UNLINKED_ACCOUNT_MESSAGE))
        return

    if update.callback_data == CALLBACK_SUMMARY_REPORT:
        text = build_summary_report_text(
            SignalRepository(session), AssetRepository(session), PriceCandleRepository(session)
        )
        provider.send_message(update.chat_id, text)
        return

    if update.callback_data == CALLBACK_SHOW_CHART:
        mark_awaiting_chart_symbol(update.chat_id)
        provider.send_message(
            update.chat_id, escape_markdown_v2("Send me a symbol, e.g. EURUSD")
        )


def _handle_possible_symbol_reply(
    update: RawTelegramUpdate, session: Session, provider: TelegramProvider
) -> None:
    if not consume_awaiting_chart_symbol(update.chat_id):
        return

    symbol = (update.text or "").strip().upper()
    asset = AssetRepository(session).get_by_symbol(symbol)
    if asset is None:
        provider.send_message(
            update.chat_id,
            escape_markdown_v2(f"Unknown symbol: {symbol}. Tap Show Chart and try again."),
        )
        return

    candles = PriceCandleRepository(session).list_recent(
        asset.id, Timeframe.M1, limit=_CHART_CANDLE_LIMIT
    )
    if not candles:
        provider.send_message(
            update.chat_id, escape_markdown_v2(f"No chart data yet for {symbol}.")
        )
        return

    image = render_candlestick_chart(symbol, candles)
    caption = format_current_price_caption(symbol, candles)
    provider.send_photo(update.chat_id, image, caption=caption)


@celery_app.task(name="telegram.send_signal", ignore_result=True)  # type: ignore[untyped-decorator]
def send_signal_telegram_task(signal_id: str) -> None:
    """Delivery hook (docs/57 §5) called after `SignalEngine.generate()`
    persists a BUY/SELL `Signal` - from both the on-demand
    `POST /signals/generate/{symbol}` route and the automatic
    `signals.generate_for_watchlist` task."""
    session = SessionLocal()
    try:
        signal = SignalRepository(session).get_by_id(uuid.UUID(signal_id))
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


@celery_app.task(name="telegram.send_signal_outcome", ignore_result=True)  # type: ignore[untyped-decorator]
def send_signal_outcome_telegram_task(signal_id: str) -> None:
    """TP/SL-hit follow-up delivery hook, called by
    `signal_monitoring_tasks.monitor_active_signals_task` once it flips a
    signal to `SUCCESSFUL`/`STOPPED_OUT` (docs/51 §10)."""
    session = SessionLocal()
    try:
        signal = SignalRepository(session).get_by_id(uuid.UUID(signal_id))
        if signal is None:
            return

        asset = AssetRepository(session).get_by_id(signal.asset_id)
        if asset is None:
            return

        telegram_service = TelegramService(
            account_repository=TelegramAccountRepository(session),
            provider=get_telegram_provider(),
        )
        telegram_service.send_outcome(signal, asset)
    finally:
        session.close()


@celery_app.task(name="telegram.send_signal_triggered", ignore_result=True)  # type: ignore[untyped-decorator]
def send_signal_triggered_telegram_task(signal_id: str) -> None:
    """Entry-confirmed follow-up delivery hook (2026-08-07), called by
    `signal_monitoring_tasks.monitor_active_signals_task` once it flips a
    signal ACTIVE -> TRIGGERED on its own (not same-candle-resolved,
    which `send_signal_outcome_telegram_task` alone covers)."""
    session = SessionLocal()
    try:
        signal = SignalRepository(session).get_by_id(uuid.UUID(signal_id))
        if signal is None:
            return

        asset = AssetRepository(session).get_by_id(signal.asset_id)
        if asset is None:
            return

        telegram_service = TelegramService(
            account_repository=TelegramAccountRepository(session),
            provider=get_telegram_provider(),
        )
        telegram_service.send_triggered(signal, asset)
    finally:
        session.close()


def enqueue_signal_outcome_delivery(signal_id: str) -> None:
    """Best-effort enqueue of `send_signal_outcome_telegram_task` - same
    "log and move on" reasoning as `enqueue_signal_delivery`: the signal's
    status has already been persisted as closed by the time this runs, a
    broker outage here must never roll that back."""
    try:
        send_signal_outcome_telegram_task.delay(signal_id)
    except Exception:
        logger.warning(
            "telegram_signal_outcome_delivery_enqueue_failed", signal_id=signal_id, exc_info=True
        )


def enqueue_signal_triggered_delivery(signal_id: str) -> None:
    """Best-effort enqueue of `send_signal_triggered_telegram_task` - same
    "log and move on" reasoning as `enqueue_signal_outcome_delivery`: the
    signal's status has already been persisted as TRIGGERED by the time
    this runs, a broker outage here must never roll that back."""
    try:
        send_signal_triggered_telegram_task.delay(signal_id)
    except Exception:
        logger.warning(
            "telegram_signal_triggered_delivery_enqueue_failed", signal_id=signal_id, exc_info=True
        )


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

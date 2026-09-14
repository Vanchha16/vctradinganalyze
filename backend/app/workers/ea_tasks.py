"""Watches the MT5 Expert Advisor terminals and tells the operator on Telegram
when one goes offline, comes back, or stops for the day at its loss limit
(ADR-170). The decision is `services/ea_terminal_watch.py`; this task only
loads, sends and records."""

from collections.abc import Callable
from datetime import UTC, datetime

import structlog

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.telegram import get_telegram_provider
from app.models.ea_token import EaToken
from app.repositories.ea_token_repository import EaTokenRepository
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services import credential_resolver, ea_terminal_watch
from app.services.ea_terminal_watch import TerminalAlert
from app.services.telegram.message_sections import (
    compose_ea_back_online_message,
    compose_ea_loss_limit_message,
    compose_ea_offline_message,
)
from app.services.telegram_service import TelegramService
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

_COMPOSERS: dict[TerminalAlert, Callable[..., str]] = {
    TerminalAlert.OFFLINE: compose_ea_offline_message,
    TerminalAlert.BACK_ONLINE: compose_ea_back_online_message,
    TerminalAlert.LOSS_LIMIT: compose_ea_loss_limit_message,
}


@celery_app.task(name="ea.watch_terminals", ignore_result=True)  # type: ignore[untyped-decorator]
def watch_terminals_task() -> None:
    """Silently no-ops while Telegram is not configured - and records nothing,
    so the first run after it is configured still alerts."""
    if not credential_resolver.resolve("telegram_bot"):
        return

    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        is_open = ea_terminal_watch.market_open(now)
        telegram = TelegramService(
            account_repository=TelegramAccountRepository(session),
            provider=get_telegram_provider(),
        )
        for token in EaTokenRepository(session).list_reporting():
            decision = ea_terminal_watch.decide(token, now, is_market_open=is_open)
            if not decision.changes(token):
                continue
            if not _send(telegram, token, decision.alerts, now):
                continue  # markers left as they were - decided again next run
            token.offline_alerted_at = decision.offline_alerted_at
            token.loss_limit_alerted_at = decision.loss_limit_alerted_at
            session.commit()
            if decision.alerts:
                logger.info(
                    "ea.terminal_alerted",
                    token_id=str(token.id),
                    alerts=[alert.value for alert in decision.alerts],
                )
    finally:
        session.close()


def _send(
    telegram: TelegramService,
    token: EaToken,
    alerts: tuple[TerminalAlert, ...],
    now: datetime,
) -> bool:
    try:
        for alert in alerts:
            telegram.send_to_operators(_COMPOSERS[alert](token, now=now))
    except Exception:
        logger.warning("ea.terminal_alert_failed", token_id=str(token.id), exc_info=True)
        return False
    return True


def register_ea_schedule() -> dict[str, dict[str, object]]:
    """Celery Beat schedule entry - mirrors
    `telegram_tasks.register_telegram_schedule`'s shape."""
    return {
        "ea-watch-terminals": {
            "task": "ea.watch_terminals",
            "schedule": float(settings.ea_watch_interval_seconds),
        }
    }

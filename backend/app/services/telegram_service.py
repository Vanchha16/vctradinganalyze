import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.signal import Signal
from app.models.telegram_account import TelegramAccount
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services.telegram.message_sections import (
    compose_signal_message,
    compose_signal_outcome_message,
    escape_markdown_v2,
)
from app.services.telegram.providers.base import TelegramProvider

_LINK_CODE_BYTES = 16
_LINK_CODE_TTL_MINUTES = 10

__all__ = ["TelegramService", "escape_markdown_v2"]


class TelegramService:
    """Account linking + message rendering (docs/57 §3/§6). No new
    decision/scoring logic - every value rendered into a message is read
    verbatim from an already-persisted `Signal`/`AIAnalysis` row (message
    composition itself lives in `telegram.message_sections`)."""

    def __init__(
        self, account_repository: TelegramAccountRepository, provider: TelegramProvider
    ) -> None:
        self._account_repository = account_repository
        self._provider = provider

    def create_link_code(self, user_id: uuid.UUID) -> TelegramAccount:
        """Issues a fresh link code for `user_id` (docs/57 §3), upserting
        the row - a new call before a prior code was used invalidates it."""
        existing = self._account_repository.get_by_user_id(user_id)
        code = secrets.token_urlsafe(_LINK_CODE_BYTES)
        expires_at = datetime.now(UTC) + timedelta(minutes=_LINK_CODE_TTL_MINUTES)

        if existing is not None:
            existing.link_code = code
            existing.link_code_expires_at = expires_at
            self._account_repository.session.flush()
            return existing

        account = TelegramAccount(
            user_id=user_id, link_code=code, link_code_expires_at=expires_at
        )
        return self._account_repository.create(account)

    def resolve_link_code(self, link_code: str, chat_id: str) -> TelegramAccount | None:
        """Called when `/start <code>` arrives (docs/57 §3). Returns
        `None` (silently, no account mutated) if the code is unknown,
        already used, or expired - the poll task replies to the user
        with a generic failure message in that case."""
        account = self._account_repository.get_by_link_code(link_code)
        if account is None or account.linked_at is not None:
            return None
        expires_at = account.link_code_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None

        account.telegram_chat_id = chat_id
        account.linked_at = datetime.now(UTC)
        self._account_repository.session.flush()
        return account

    def get_account(self, user_id: uuid.UUID) -> TelegramAccount | None:
        return self._account_repository.get_by_user_id(user_id)

    def unlink(self, user_id: uuid.UUID) -> None:
        account = self._account_repository.get_by_user_id(user_id)
        if account is not None:
            self._account_repository.delete(account)

    def linked_accounts(self) -> list[TelegramAccount]:
        return self._account_repository.list_linked()

    def send_signal(
        self, signal: Signal, analysis: AIAnalysis, asset: Asset, *, now: datetime | None = None
    ) -> None:
        """Broadcasts one Signal to every linked account (ADR-113 - no
        per-user filtering yet)."""
        text = compose_signal_message(signal, analysis, asset, now=now or datetime.now(UTC))
        for account in self.linked_accounts():
            if account.telegram_chat_id is None:
                continue
            self._provider.send_message(account.telegram_chat_id, text)

    def send_outcome(self, signal: Signal, asset: Asset, *, now: datetime | None = None) -> None:
        """Broadcasts a TP/SL-hit follow-up for a `signal` already
        transitioned to `SUCCESSFUL`/`STOPPED_OUT` by
        `signal_monitoring_tasks.monitor_active_signals_task`."""
        text = compose_signal_outcome_message(signal, asset, now=now or datetime.now(UTC))
        for account in self.linked_accounts():
            if account.telegram_chat_id is None:
                continue
            self._provider.send_message(account.telegram_chat_id, text)

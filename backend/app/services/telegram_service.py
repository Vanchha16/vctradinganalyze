import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import SignalType
from app.models.signal import Signal
from app.models.telegram_account import TelegramAccount
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services.telegram.providers.base import TelegramProvider

_LINK_CODE_BYTES = 16
_LINK_CODE_TTL_MINUTES = 10

# MarkdownV2 requires escaping these literal characters outside of an
# already-applied entity (docs/57 §6) - values interpolated into the
# signal message (symbol, price strings, evidence bullets) are free text
# from elsewhere in the system and must be escaped before sending.
_MARKDOWN_V2_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_markdown_v2(text: str) -> str:
    return re.sub(f"([{re.escape(_MARKDOWN_V2_SPECIAL_CHARS)}])", r"\\\1", text)


class TelegramService:
    """Account linking + message rendering (docs/57 §3/§6). No new
    decision/scoring logic - every value rendered into a message is read
    verbatim from an already-persisted `Signal`/`AIAnalysis` row."""

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

    def send_signal(self, signal: Signal, analysis: AIAnalysis, asset: Asset) -> None:
        """Broadcasts one Signal to every linked account (ADR-113 - no
        per-user filtering yet)."""
        text = self._render_signal_message(signal, analysis, asset)
        for account in self.linked_accounts():
            if account.telegram_chat_id is None:
                continue
            self._provider.send_message(account.telegram_chat_id, text)

    def _render_signal_message(self, signal: Signal, analysis: AIAnalysis, asset: Asset) -> str:
        """docs/57 §6's verbatim template."""
        direction_emoji = "\U0001f4c8" if signal.signal_type == SignalType.BUY else "\U0001f4c9"
        direction = escape_markdown_v2(signal.signal_type.value.upper())
        symbol = escape_markdown_v2(asset.symbol)

        lines = [
            f"{direction_emoji} *{direction} {symbol}*",
            "",
            f"Confidence: {escape_markdown_v2(f'{signal.confidence:.0f}%')}",
            f"Entry: {escape_markdown_v2(str(signal.entry_price))}",
            f"Stop Loss: {escape_markdown_v2(str(signal.stop_loss))}",
            f"Take Profit: {escape_markdown_v2(str(signal.take_profit))}",
        ]
        if analysis.risk_level:
            lines.append(f"Risk: {escape_markdown_v2(analysis.risk_level.title())}")

        evidence = analysis.supporting_evidence[:3]
        if evidence:
            lines.append("")
            lines.append("Reason:")
            lines.extend(f"• {escape_markdown_v2(item)}" for item in evidence)

        return "\n".join(lines)

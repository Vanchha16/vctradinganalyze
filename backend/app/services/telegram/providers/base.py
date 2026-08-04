from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawTelegramUpdate:
    """A single Telegram `getUpdates` update, before command parsing
    (docs/57 §4). Only the `/start <code>` command is interpreted in this
    phase - every other message type is ignored by the caller."""

    update_id: int
    chat_id: str
    text: str | None


class TelegramProvider(Protocol):
    """Interface every Telegram transport implements (docs/57 §4).

    `TelegramService` depends only on this interface, never on a
    concrete provider class - mirrors
    `app.services.news.providers.base.NewsProvider`.
    """

    name: str

    def send_message(self, chat_id: str, text: str) -> None:
        """Send a Markdown-formatted message to `chat_id`.

        Raises `TransientTelegramProviderError` for retryable failures,
        `PermanentTelegramProviderError` for failures that should not be
        retried (e.g. the user blocked the bot).
        """
        ...

    def get_updates(self, offset: int | None) -> list[RawTelegramUpdate]:
        """Long-poll for updates since `offset` (exclusive)."""
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not send a real message."""
        ...


__all__ = ["RawTelegramUpdate", "TelegramProvider"]

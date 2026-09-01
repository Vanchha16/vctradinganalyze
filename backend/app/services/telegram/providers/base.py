from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RawTelegramUpdate:
    """A single Telegram `getUpdates` update, before command parsing
    (docs/57 §4/§13). `/start <code>` and free-text symbol replies come
    through as `text` on a `message` update; a tapped inline button
    (Summary Report / Show Chart, §13) comes through as a `callback_query`
    update instead - `callback_query_id`/`callback_data` are `None` for a
    plain message, and `text` is `None` for a plain callback."""

    update_id: int
    chat_id: str
    text: str | None
    callback_query_id: str | None = None
    callback_data: str | None = None


class TelegramProvider(Protocol):
    """Interface every Telegram transport implements (docs/57 §4).

    `TelegramService` depends only on this interface, never on a
    concrete provider class - mirrors
    `app.services.news.providers.base.NewsProvider`.
    """

    name: str

    def send_message(
        self, chat_id: str, text: str, *, reply_markup: dict[str, Any] | None = None
    ) -> None:
        """Send a Markdown-formatted message to `chat_id`, optionally with
        an inline keyboard (§13's Summary Report/Show Chart buttons -
        `app.services.telegram.keyboards`).

        Raises `TransientTelegramProviderError` for retryable failures,
        `PermanentTelegramProviderError` for failures that should not be
        retried (e.g. the user blocked the bot).
        """
        ...

    def send_photo(
        self,
        chat_id: str,
        photo: bytes,
        *,
        caption: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        """Send a PNG chart image to `chat_id` (§13's Show Chart button),
        optionally restoring a keyboard (e.g. the persistent main menu,
        after a one-time symbol-picker keyboard has served its purpose).

        Same error classification as `send_message`.
        """
        ...

    def answer_callback_query(self, callback_query_id: str, *, text: str | None = None) -> None:
        """Acknowledges a tapped inline button so Telegram stops showing
        the client-side loading spinner - must be called for every
        `callback_query` update, whether or not `text` is shown as a
        toast. Best-effort: a failure here must never block handling the
        button press itself."""
        ...

    def get_updates(self, offset: int | None) -> list[RawTelegramUpdate]:
        """Long-poll for updates since `offset` (exclusive)."""
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not send a real message."""
        ...


__all__ = ["RawTelegramUpdate", "TelegramProvider"]

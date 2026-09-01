from typing import Any

from app.services.telegram.providers.base import RawTelegramUpdate


class MockTelegramProvider:
    """In-memory Telegram provider for tests/dev without a real bot token
    (docs/57 §4) - never calls the network. `sent_messages`/`sent_photos`/
    `answered_callback_queries` are inspectable by tests, mirroring every
    other provider's mock shape."""

    name = "mock"

    def __init__(self) -> None:
        self.sent_messages: list[tuple[str, str, dict[str, Any] | None]] = []
        self.sent_photos: list[tuple[str, bytes, str | None]] = []
        self.answered_callback_queries: list[tuple[str, str | None]] = []

    def send_message(
        self, chat_id: str, text: str, *, reply_markup: dict[str, Any] | None = None
    ) -> None:
        self.sent_messages.append((chat_id, text, reply_markup))

    def send_photo(self, chat_id: str, photo: bytes, *, caption: str | None = None) -> None:
        self.sent_photos.append((chat_id, photo, caption))

    def answer_callback_query(self, callback_query_id: str, *, text: str | None = None) -> None:
        self.answered_callback_queries.append((callback_query_id, text))

    def get_updates(self, offset: int | None) -> list[RawTelegramUpdate]:
        return []

    def health_check(self) -> bool:
        return True

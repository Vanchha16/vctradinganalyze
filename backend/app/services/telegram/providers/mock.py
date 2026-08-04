from app.services.telegram.providers.base import RawTelegramUpdate


class MockTelegramProvider:
    """In-memory Telegram provider for tests/dev without a real bot token
    (docs/57 §4) - never calls the network. `sent_messages` is inspectable
    by tests, mirroring every other provider's mock shape."""

    name = "mock"

    def __init__(self) -> None:
        self.sent_messages: list[tuple[str, str]] = []

    def send_message(self, chat_id: str, text: str) -> None:
        self.sent_messages.append((chat_id, text))

    def get_updates(self, offset: int | None) -> list[RawTelegramUpdate]:
        return []

    def health_check(self) -> bool:
        return True

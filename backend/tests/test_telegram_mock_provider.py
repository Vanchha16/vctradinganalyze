from app.services.telegram.providers.mock import MockTelegramProvider


def test_send_message_records_text_and_reply_markup() -> None:
    provider = MockTelegramProvider()
    keyboard = {"inline_keyboard": []}

    provider.send_message("123", "hello", reply_markup=keyboard)

    assert provider.sent_messages == [("123", "hello", keyboard)]


def test_send_message_records_none_reply_markup_by_default() -> None:
    provider = MockTelegramProvider()

    provider.send_message("123", "hello")

    assert provider.sent_messages == [("123", "hello", None)]


def test_send_photo_records_chat_photo_and_caption() -> None:
    provider = MockTelegramProvider()

    provider.send_photo("123", b"png-bytes", caption="EURUSD")

    assert provider.sent_photos == [("123", b"png-bytes", "EURUSD")]


def test_answer_callback_query_records_id_and_text() -> None:
    provider = MockTelegramProvider()

    provider.answer_callback_query("cbq-1", text="ok")

    assert provider.answered_callback_queries == [("cbq-1", "ok")]


def test_get_updates_returns_empty_and_health_check_is_true() -> None:
    provider = MockTelegramProvider()

    assert provider.get_updates(None) == []
    assert provider.health_check() is True

import json

import httpx
import pytest

from app.services.telegram.providers.bot_api import BotApiProvider
from app.services.telegram.providers.exceptions import PermanentTelegramProviderError


def _provider(handler: httpx.MockTransport) -> BotApiProvider:
    return BotApiProvider(
        bot_token="test-token",
        base_url="https://api.telegram.org",
        timeout=5.0,
        transport=handler,
    )


def test_send_message_includes_reply_markup_when_given() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {}})

    provider = _provider(httpx.MockTransport(handler))
    keyboard = {"inline_keyboard": [[{"text": "Tap", "callback_data": "x"}]]}

    provider.send_message("123", "hello", reply_markup=keyboard)

    assert captured["reply_markup"] == keyboard


def test_send_message_omits_reply_markup_when_not_given() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {}})

    provider = _provider(httpx.MockTransport(handler))

    provider.send_message("123", "hello")

    assert "reply_markup" not in captured


def test_send_photo_uploads_multipart_with_chat_id_and_caption() -> None:
    captured_fields: dict[str, str] = {}
    captured_photo_present = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_photo_present
        body = request.read().decode("latin-1")
        captured_photo_present = "chart.png" in body and "image/png" in body
        # multipart bodies aren't trivially json-decodable; assert on the
        # raw body containing our known field values instead.
        captured_fields["chat_id_present"] = "123" in body
        captured_fields["caption_present"] = "EURUSD" in body
        return httpx.Response(200, json={"ok": True, "result": {}})

    provider = _provider(httpx.MockTransport(handler))

    provider.send_photo("123", b"\x89PNG-fake-bytes", caption="EURUSD")

    assert captured_photo_present
    assert captured_fields["chat_id_present"]
    assert captured_fields["caption_present"]


def test_send_photo_json_encodes_reply_markup_for_multipart_body() -> None:
    body_text = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal body_text
        body_text = request.read().decode("latin-1")
        return httpx.Response(200, json={"ok": True, "result": {}})

    provider = _provider(httpx.MockTransport(handler))
    keyboard = {"keyboard": [[{"text": "EURUSD"}]], "resize_keyboard": True}

    provider.send_photo("123", b"\x89PNG-fake-bytes", reply_markup=keyboard)

    # multipart/form-data has no top-level JSON to decode - the Bot API
    # requires reply_markup to be sent as a JSON-*string* field there,
    # unlike sendMessage's raw JSON body, so assert on that substring.
    assert json.dumps(keyboard) in body_text


def test_send_photo_raises_permanent_error_on_bad_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "chat not found"})

    provider = _provider(httpx.MockTransport(handler))

    with pytest.raises(PermanentTelegramProviderError):
        provider.send_photo("bad-chat", b"data")


def test_answer_callback_query_posts_callback_id() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": True})

    provider = _provider(httpx.MockTransport(handler))

    provider.answer_callback_query("cbq-1", text="Loading...")

    assert captured == {"callback_query_id": "cbq-1", "text": "Loading..."}


def test_get_updates_parses_callback_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {
                        "update_id": 42,
                        "callback_query": {
                            "id": "cbq-99",
                            "data": "show_chart",
                            "message": {"chat": {"id": 555}},
                        },
                    }
                ],
            },
        )

    provider = _provider(httpx.MockTransport(handler))

    updates = provider.get_updates(None)

    assert len(updates) == 1
    update = updates[0]
    assert update.update_id == 42
    assert update.chat_id == "555"
    assert update.text is None
    assert update.callback_query_id == "cbq-99"
    assert update.callback_data == "show_chart"


def test_get_updates_still_parses_plain_messages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {"chat": {"id": 1}, "text": "/start abc"},
                    }
                ],
            },
        )

    provider = _provider(httpx.MockTransport(handler))

    updates = provider.get_updates(None)

    assert updates[0].text == "/start abc"
    assert updates[0].callback_query_id is None


def test_get_updates_skips_callback_query_without_chat() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {"update_id": 1, "callback_query": {"id": "cbq", "data": "x", "message": {}}}
                ],
            },
        )

    provider = _provider(httpx.MockTransport(handler))

    assert provider.get_updates(None) == []

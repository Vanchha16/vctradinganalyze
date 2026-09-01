import json
from typing import Any, NoReturn

import httpx

from app.services.telegram.providers.base import RawTelegramUpdate
from app.services.telegram.providers.bot_api_http import (
    TelegramBotHttpClient,
    TelegramTransportError,
)
from app.services.telegram.providers.exceptions import (
    PermanentTelegramProviderError,
    TransientTelegramProviderError,
)

# Telegram's `getUpdates` supports a long-poll `timeout` param, but this
# provider is driven by a Celery Beat tick every
# `settings.telegram_poll_interval_seconds` (ADR-112) rather than one
# dedicated always-running poll loop - a short/immediate timeout avoids
# a single task run blocking past the next scheduled tick and stacking
# overlapping runs.
_GET_UPDATES_TIMEOUT_SECONDS = "0"


class TelegramAuthenticationError(PermanentTelegramProviderError):
    """The bot token was rejected (401)."""


class TelegramRateLimitedError(TransientTelegramProviderError):
    """Telegram's own rate limit was hit (429)."""


class BotApiProvider:
    """Real Telegram Bot API implementation of `TelegramProvider`
    (docs/57 §4) - long-polling `getUpdates`, not a webhook (ADR-112)."""

    name = "bot_api"

    def __init__(
        self,
        bot_token: str,
        base_url: str,
        timeout: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = TelegramBotHttpClient(
            base_url=base_url, bot_token=bot_token, timeout=timeout, transport=transport
        )

    def send_message(
        self, chat_id: str, text: str, *, reply_markup: dict[str, Any] | None = None
    ) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        try:
            status_code, body = self._http.post("/sendMessage", payload)
        except TelegramTransportError as exc:
            raise TransientTelegramProviderError(f"telegram: {exc}") from exc

        if status_code == 200 and body.get("ok"):
            return
        self._raise_for_error(status_code, body)

    def send_photo(
        self,
        chat_id: str,
        photo: bytes,
        *,
        caption: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        data = {"chat_id": chat_id}
        if caption is not None:
            data["caption"] = caption
        if reply_markup is not None:
            # Unlike sendMessage's raw JSON body, sendPhoto is a
            # multipart/form-data request - the Bot API requires
            # reply_markup to arrive as a JSON-encoded *string* field
            # here, not a nested object.
            data["reply_markup"] = json.dumps(reply_markup)

        try:
            status_code, body = self._http.post_multipart(
                "/sendPhoto", data, {"photo": ("chart.png", photo, "image/png")}
            )
        except TelegramTransportError as exc:
            raise TransientTelegramProviderError(f"telegram: {exc}") from exc

        if status_code == 200 and body.get("ok"):
            return
        self._raise_for_error(status_code, body)

    def answer_callback_query(self, callback_query_id: str, *, text: str | None = None) -> None:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text is not None:
            payload["text"] = text

        try:
            status_code, body = self._http.post("/answerCallbackQuery", payload)
        except TelegramTransportError as exc:
            raise TransientTelegramProviderError(f"telegram: {exc}") from exc

        if status_code == 200 and body.get("ok"):
            return
        self._raise_for_error(status_code, body)

    def get_updates(self, offset: int | None) -> list[RawTelegramUpdate]:
        params = {"timeout": _GET_UPDATES_TIMEOUT_SECONDS}
        if offset is not None:
            params["offset"] = str(offset)

        try:
            status_code, body = self._http.get("/getUpdates", params)
        except TelegramTransportError as exc:
            raise TransientTelegramProviderError(f"telegram: {exc}") from exc

        if status_code == 200 and body.get("ok"):
            return self._parse_updates(body)
        self._raise_for_error(status_code, body)

    def _parse_updates(self, body: dict[str, object]) -> list[RawTelegramUpdate]:
        results = body.get("result", [])
        if not isinstance(results, list):
            return []

        updates: list[RawTelegramUpdate] = []
        for row in results:
            callback_query = row.get("callback_query")
            if isinstance(callback_query, dict):
                message = callback_query.get("message")
                chat = message.get("chat", {}) if isinstance(message, dict) else {}
                if not chat.get("id"):
                    # A callback on an inline-mode message (no `chat`) -
                    # nothing this bot's poll loop can reply to; skip it
                    # rather than crash on a missing chat id.
                    continue
                updates.append(
                    RawTelegramUpdate(
                        update_id=int(row["update_id"]),
                        chat_id=str(chat.get("id", "")),
                        text=None,
                        callback_query_id=str(callback_query.get("id", "")),
                        callback_data=callback_query.get("data"),
                    )
                )
                continue

            message = row.get("message")
            if not isinstance(message, dict):
                continue
            chat = message.get("chat", {})
            updates.append(
                RawTelegramUpdate(
                    update_id=int(row["update_id"]),
                    chat_id=str(chat.get("id", "")),
                    text=message.get("text"),
                )
            )
        return updates

    def _raise_for_error(self, status_code: int, body: dict[str, object]) -> NoReturn:
        message = str(body.get("description", f"HTTP {status_code}"))

        if status_code == 401:
            raise TelegramAuthenticationError(f"telegram: {message}")
        if status_code == 429:
            raise TelegramRateLimitedError(f"telegram: {message}")
        if status_code >= 500:
            raise TransientTelegramProviderError(f"telegram: {message}")
        raise PermanentTelegramProviderError(f"telegram: {message}")

    def health_check(self) -> bool:
        try:
            status_code, body = self._http.get("/getMe", {})
        except TelegramTransportError:
            return False
        return status_code == 200 and body.get("ok") is True

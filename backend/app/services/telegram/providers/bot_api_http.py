from typing import Any

import httpx


class TelegramTransportError(Exception):
    """A network-level failure (timeout, connection error, malformed
    response body) - distinct from a business-level API error (bad
    token, chat not found), which `BotApiProvider` classifies from a
    successfully-received response. Mirrors `TwelveDataTransportError`."""


class TelegramBotHttpClient:
    """Isolates raw HTTP transport (httpx, base URL, timeout) from
    `BotApiProvider`'s job of interpreting the Telegram Bot API's
    `{"ok": bool, ...}` envelope - mirrors `TwelveDataHttpClient`.
    """

    def __init__(
        self,
        base_url: str,
        bot_token: str,
        timeout: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """`transport` is exposed only so tests can inject
        `httpx.MockTransport`; production code never needs to pass it."""
        self._client = httpx.Client(
            base_url=f"{base_url}/bot{bot_token}", timeout=timeout, transport=transport
        )

    def get(self, path: str, params: dict[str, str]) -> tuple[int, dict[str, Any]]:
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise TelegramTransportError(str(exc)) from exc
        return self._decode(response)

    def post(self, path: str, json: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        try:
            response = self._client.post(path, json=json)
        except httpx.HTTPError as exc:
            raise TelegramTransportError(str(exc)) from exc
        return self._decode(response)

    def _decode(self, response: httpx.Response) -> tuple[int, dict[str, Any]]:
        try:
            body = response.json()
        except ValueError as exc:
            raise TelegramTransportError(f"invalid JSON response: {exc}") from exc
        return response.status_code, body

    def close(self) -> None:
        self._client.close()

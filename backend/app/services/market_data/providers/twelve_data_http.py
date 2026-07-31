from typing import Any

import httpx


class TwelveDataTransportError(Exception):
    """A network-level failure (timeout, connection error, malformed
    response body) - distinct from a business-level API error (bad symbol,
    quota exceeded), which `TwelveDataProvider` classifies from a
    successfully-received response (docs/40 §5)."""


class TwelveDataHttpClient:
    """Isolates raw HTTP transport (httpx, base URL, auth header, timeout)
    from `TwelveDataProvider`'s job of interpreting Twelve Data's response
    shape and classifying errors into the shared exception hierarchy.

    Deliberately thin: it performs the request and returns
    `(status_code, json_body)`, without inspecting Twelve Data's own
    `{"status": "ok"/"error", ...}` envelope - that's response-schema
    interpretation, which belongs to the provider, not the transport.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """`transport` is exposed only so tests can inject
        `httpx.MockTransport` (docs/40 §10 - no real API calls in the
        standard test run); production code never needs to pass it."""
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": f"apikey {api_key}"},
            transport=transport,
        )

    def get(self, path: str, params: dict[str, str]) -> tuple[int, dict[str, Any]]:
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise TwelveDataTransportError(str(exc)) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise TwelveDataTransportError(f"invalid JSON response: {exc}") from exc

        return response.status_code, body

    def close(self) -> None:
        self._client.close()

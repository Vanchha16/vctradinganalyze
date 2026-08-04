from typing import Any

import httpx


class NewsApiTransportError(Exception):
    """A network-level failure (timeout, connection error, malformed
    response body) - distinct from a business-level API error (bad key,
    rate limit), which `NewsApiProvider` classifies from a successfully-
    received response. Mirrors `TwelveDataTransportError`'s split between
    transport and provider concerns."""


class NewsApiHttpClient:
    """Isolates raw HTTP transport (httpx, base URL, auth header, timeout)
    from `NewsApiProvider`'s job of interpreting NewsAPI.org's response
    shape and classifying errors - mirrors `TwelveDataHttpClient`.
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
        `httpx.MockTransport`; production code never needs to pass it."""
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"X-Api-Key": api_key},
            transport=transport,
        )

    def get(self, path: str, params: dict[str, str]) -> tuple[int, dict[str, Any]]:
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise NewsApiTransportError(str(exc)) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise NewsApiTransportError(f"invalid JSON response: {exc}") from exc

        return response.status_code, body

    def close(self) -> None:
        self._client.close()

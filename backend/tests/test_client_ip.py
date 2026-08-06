"""Phase 9A (ADR-132) - `app.core.client_ip.get_client_ip`, the single
shared helper for both the audit-trail IP (`auth.py`, `admin_users.py`,
`admin_system.py`) and the per-IP rate limiter
(`app/dependencies/rate_limit.py`).

The security-critical case: `get_client_ip` itself never parses
`X-Forwarded-For` - it only ever reads `request.client.host`. Trusting a
forwarded header from an *untrusted* peer is uvicorn's job to refuse, not
this module's; this module deliberately has no branch that could get that
wrong. These tests exercise both directions of what that implies:
uvicorn's `ProxyHeadersMiddleware` rewriting `request.client` when the
immediate peer is trusted, and leaving it alone (the raw TCP peer) when
it is not - proven through a real `TestClient`, not a hand-built ASGI
scope, so the whole real chain (middleware -> `Request` -> this helper)
is exercised.
"""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.client_ip import get_client_ip


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/whoami")
    def _whoami(request: Request) -> dict[str, str | None]:
        return {"ip": get_client_ip(request)}

    return app


def test_forwarded_for_is_trusted_from_a_configured_trusted_peer() -> None:
    """The normal production case: Nginx (127.0.0.1) is the immediate TCP
    peer and is in `forwarded_allow_ips`, so uvicorn rewrites
    `request.client` to the real client from `X-Forwarded-For` before the
    app ever sees the request."""
    # TestClient's own transport always connects as "testclient" - that IS
    # the immediate peer uvicorn would see, so trusting it here mirrors
    # trusting 127.0.0.1 in production.
    client = TestClient(
        ProxyHeadersMiddleware(_build_app(), trusted_hosts="testclient"),
        client=("testclient", 50000),
    )

    response = client.get("/whoami", headers={"X-Forwarded-For": "203.0.113.7"})

    assert response.json()["ip"] == "203.0.113.7"


def test_forwarded_for_is_not_trusted_from_an_untrusted_peer() -> None:
    """The security-critical case this whole module exists for: if the
    immediate peer is not a configured trusted proxy - e.g. an attacker
    connecting directly to uvicorn, bypassing Nginx entirely - its forged
    `X-Forwarded-For` must be ignored. `request.client` stays the real,
    untrusted TCP peer, not whatever the attacker claims."""
    client = TestClient(
        ProxyHeadersMiddleware(_build_app(), trusted_hosts="203.0.113.99"),
        client=("testclient", 50000),
    )

    response = client.get("/whoami", headers={"X-Forwarded-For": "203.0.113.7"})

    # "testclient" (the untrusted immediate peer), NOT the forged header.
    assert response.json()["ip"] == "testclient"


def test_returns_none_when_request_has_no_client() -> None:
    request = Request({"type": "http", "client": None, "headers": []})

    assert get_client_ip(request) is None


def test_returns_the_host_when_client_is_present() -> None:
    request = Request({"type": "http", "client": ("203.0.113.7", 12345), "headers": []})

    assert get_client_ip(request) == "203.0.113.7"

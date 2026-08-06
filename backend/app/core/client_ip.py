"""Single source of truth for resolving a request's client IP (Phase 9A,
ADR-132). Previously duplicated three times - `admin_system.py`'s and
`admin_users.py`'s own `_client_ip` helpers, plus an inline expression in
`auth.py`'s login route - each doing the exact same thing. Unified here so
the audit-trail path (`authentication_service.py`, `admin_user_service.py`,
`admin_system_service.py`) and the per-IP rate limiter
(`app/dependencies/rate_limit.py`) always agree on what "the client IP" is.

Deliberately does NOT parse `X-Forwarded-For` itself. That header is
attacker-controlled - any client can send it - so trusting it
unconditionally would let an attacker both bypass the per-IP rate limit
(by rotating a fake value) and poison the audit trail, which is strictly
worse than not resolving a real client IP at all.

`request.client.host` is trusted instead. Locally, with no reverse proxy
in front, it already is the real peer. In production, Nginx sits in front
(docs/27) - uvicorn's own `ProxyHeadersMiddleware` (enabled via
`--proxy-headers --forwarded-allow-ips <settings.trusted_proxy_ips>`, see
`backend/scripts/run_dev.py` and docs/60 §4.1) rewrites `request.client`
from `X-Forwarded-For`/`X-Forwarded-Proto` *before* the app ever sees the
request, and only does so when the immediate TCP peer matches a
configured trusted proxy address - an untrusted peer's forged header is
never applied. This module doesn't need to know which case it's in.
"""

from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None

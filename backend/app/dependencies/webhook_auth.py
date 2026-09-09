"""Access control for the inbound TradingView webhook (ADR-146).

**Why a URL-path token and not a header.** TradingView's alert UI lets
you set a webhook URL and a JSON message body. It does not let you set
request headers, so `Authorization`/`X-Signature` - the mechanisms every
other authenticated surface in this project uses - are simply not
available. The secret has to travel in the URL or the body. The URL is
the lesser evil: a body-embedded secret would be duplicated into every
alert template and shown in TradingView's message editor next to the
data it protects.

**Fail-closed, matching `metrics_auth.require_metrics_token`.** An unset
`tradingview_webhook_secret` (the default) means the webhook was never
deliberately enabled, so the route returns 404 - not 403, not an empty
200 - and does not advertise its own existence. A wrong token gets the
identical 404: nothing distinguishes "not configured" from "wrong
secret" from "no such route".

**Consequences an operator should know.** A URL token is bearer
authentication: anyone who obtains the URL can post alerts. It appears
in TradingView's stored alert config and may appear in reverse-proxy
access logs. Mitigations in place: the secret is compared with
`hmac.compare_digest` (no timing oracle), the route is per-IP rate
limited like every other public surface (ADR-132's Phase 9A work), and
an accepted alert is *recorded and notified*, never executed as a trade
(ADR-146 §Decision). Rotation is a config change plus re-pointing the
TradingView alerts; there is no revocation list, and there is no second
factor. This is the standard TradingView webhook pattern, adopted with
its limits stated rather than assumed away.
"""

import hmac

from app.config import settings
from app.exceptions import ResourceNotFoundException


def verify_webhook_token(token: str) -> None:
    """Raises `ResourceNotFoundException` (404) unless `token` matches
    the configured secret. Not a FastAPI `Depends` because the token
    arrives as a path parameter the route already declares - the route
    calls this directly."""
    secret = settings.tradingview_webhook_secret
    if not secret or not hmac.compare_digest(token, secret):
        raise ResourceNotFoundException("Not Found")


__all__ = ["verify_webhook_token"]

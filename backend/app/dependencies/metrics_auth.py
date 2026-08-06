"""Access control for `GET /metrics` (Phase 9D, ADR-136).

Fail-closed, not `require_admin`: a static bearer token, checked without
touching the database, so scrapers (which cannot hold a user session)
keep working even when the database is unhealthy - exactly when metrics
matter most. `settings.metrics_auth_token` defaults to empty, which
means metrics were never deliberately enabled - the endpoint returns
404, not 403 or an empty 200, so it does not advertise its own
existence. A wrong or missing token gets the identical 404; there is no
separate response that would let an outside caller distinguish "not
configured" from "wrong token" from "route doesn't exist".
"""

import hmac
from typing import Annotated

from fastapi import Header

from app.config import settings
from app.exceptions import ResourceNotFoundException


def require_metrics_token(authorization: Annotated[str | None, Header()] = None) -> None:
    token = settings.metrics_auth_token
    provided = (authorization or "").removeprefix("Bearer ")
    if not token or not hmac.compare_digest(provided, token):
        raise ResourceNotFoundException("Not Found")

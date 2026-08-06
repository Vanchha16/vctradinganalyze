"""Prometheus HTTP request metrics (Phase 9D, ADR-136).

Labels by the matched route *template* (e.g.
`/api/v1/analysis/technical/{symbol}`), never the raw request path -
labeling by raw path would create one time series per symbol per
timeframe per status: unbounded cardinality, held in memory forever, a
real availability risk on this project's 911MB production box already
~330MB into swap (BACKLOG.md §10). FastAPI/Starlette record the matched
route on `request.scope["route"]` once routing resolves; `call_next`
triggers that resolution, so it is already set by the time this
middleware reads it on the way back out. Paths that match no route at
all (probes, typos - genuine 404s) collapse into a single `"unmatched"`
bucket for the same cardinality reason.

`/metrics` itself is excluded from these counters entirely - otherwise
every scrape would inflate the numbers it reports, which is both noise
and a mildly confusing feedback loop.
"""

import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests received, labeled by method/route template/status.",
    ["method", "route", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds, labeled by method/route template.",
    ["method", "route"],
)

_METRICS_PATH = f"{settings.api_v1_prefix}/metrics"


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == _METRICS_PATH:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = _route_template(request)
        status = str(response.status_code)
        REQUEST_COUNT.labels(method=request.method, route=route, status=status).inc()
        REQUEST_LATENCY.labels(method=request.method, route=route).observe(duration)
        return response

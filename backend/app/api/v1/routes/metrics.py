"""`GET /metrics` (Phase 9D, ADR-136) - Prometheus text-format exposition
of request counts/latency (`app/middleware/metrics.py`) plus the
`prometheus_client` default process/GC collectors.

Deliberately not wired into `app/api/v1/router.py`'s per-IP rate-limit
dependencies (docs/60 §4.2) - a scraper polling every 15s must never be
throttled, the same reason `/health*` is excluded. Gated by
`require_metrics_token` instead of `require_admin`: see
`app/dependencies/metrics_auth.py`.
"""

from fastapi import APIRouter, Depends
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.dependencies.metrics_auth import require_metrics_token

router = APIRouter()


@router.get("/metrics", dependencies=[Depends(require_metrics_token)])
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

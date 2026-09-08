"""`GET /admin/api-usage` response shape (ADR-144)."""

from pydantic import BaseModel


class ApiUsageRouteResponse(BaseModel):
    method: str
    #: The matched route *template*, or the literal `"unmatched"` bucket
    #: for paths that resolved to no route at all (probes, typos) -
    #: ADR-136's cardinality guard, surfaced here because a spike in it
    #: is a useful signal that someone is scanning the API.
    route: str
    requests: int
    errors: int
    #: 0.0-1.0, not a percentage - formatting is the UI's job.
    error_rate: float
    #: `None` when no latency was observed for this label pair.
    avg_latency_ms: float | None
    #: Approximate: the upper bound of the histogram bucket containing
    #: the 95th percentile, so bucket-width-accurate at best, and `None`
    #: when the percentile falls in the `+Inf` bucket.
    p95_latency_ms: float | None


class AdminApiUsageResponse(BaseModel):
    """**Cumulative since the API process started, not a time series.**
    Every counter resets on restart/deploy - the UI must say so rather
    than implying these are all-time or windowed figures."""

    total_requests: int
    total_errors: int
    error_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    route_count: int
    status_2xx: int
    status_3xx: int
    status_4xx: int
    status_5xx: int
    routes: list[ApiUsageRouteResponse]

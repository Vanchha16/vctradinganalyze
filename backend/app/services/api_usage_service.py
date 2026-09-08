"""Aggregates the Prometheus request metrics (`app/middleware/metrics.py`,
ADR-136) into a JSON snapshot for the Admin API Usage page (ADR-144).

Reads the in-process `prometheus_client` registry directly rather than
scraping `GET /metrics` over HTTP and parsing the text exposition: same
process, same numbers, no self-call, no need to hand the API its own
`METRICS_AUTH_TOKEN`. `/metrics` stays the machine-readable surface for
a real scraper; this is the human one.

**These are cumulative counters since process start, not a time series.**
Prometheus stores history in the *server* that scrapes it; this project
runs no such server, so nothing here can show a trend, a rate-per-minute,
or a comparison against yesterday - and every counter resets to zero on
each restart/deploy. The UI says "since restart" for exactly that reason.
Adding real history means running Prometheus + Grafana, which is its own
decision (and a poor fit for the 911MB production box, BACKLOG.md §10).
"""

from dataclasses import dataclass

from prometheus_client import REGISTRY
from prometheus_client.registry import CollectorRegistry

_COUNT_METRIC = "http_requests_total"
_LATENCY_METRIC = "http_request_duration_seconds"

#: The percentile the UI reports alongside the mean. Interpolated from
#: `Histogram` buckets, so it is an approximation bounded by bucket
#: width - honest for "is this route slow?", not for an SLA.
_PERCENTILE = 0.95


@dataclass(frozen=True, slots=True)
class RouteUsage:
    """One `(method, route template)` pair. `route` is the template
    (`/analysis/technical/{symbol}`), never a raw path - ADR-136 labels
    that way deliberately to bound cardinality, so this page cannot
    break down by symbol either."""

    method: str
    route: str
    requests: int
    errors: int
    error_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None


@dataclass(frozen=True, slots=True)
class ApiUsageSnapshot:
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
    routes: list[RouteUsage]


def _status_class(status: str) -> int:
    """`"404"` -> `4`. Returns 0 for anything unparseable so a malformed
    label can never crash the page."""
    return int(status[0]) if status[:1].isdigit() else 0


def _percentile_from_buckets(buckets: list[tuple[float, float]], total: float) -> float | None:
    """Linear-free bucket lookup: the upper bound of the first bucket
    whose cumulative count reaches the target rank. Deliberately not
    interpolated within the bucket - reporting `le` directly is the
    conservative reading (an over-estimate, never an under-estimate),
    and pretending to sub-bucket precision the data does not have would
    be worse than a slightly pessimistic number."""
    if total <= 0 or not buckets:
        return None
    target = total * _PERCENTILE
    for upper, cumulative in sorted(buckets):
        if cumulative >= target:
            # `+Inf` means everything above the last finite bucket; there
            # is no meaningful number to report for it.
            return None if upper == float("inf") else upper
    return None


def build_snapshot(registry: CollectorRegistry | None = None) -> ApiUsageSnapshot:
    """Collect and fold the registry into one snapshot. `registry` is
    injectable so tests can build an isolated one rather than depending
    on whatever the global registry happens to hold after other tests
    have made requests through the middleware."""
    source = registry if registry is not None else REGISTRY

    counts: dict[tuple[str, str], int] = {}
    errors: dict[tuple[str, str], int] = {}
    status_classes: dict[int, int] = {}

    latency_sums: dict[tuple[str, str], float] = {}
    latency_counts: dict[tuple[str, str], float] = {}
    latency_buckets: dict[tuple[str, str], list[tuple[float, float]]] = {}

    for metric in source.collect():
        for sample in metric.samples:
            labels = sample.labels
            if sample.name == _COUNT_METRIC:
                key = (labels["method"], labels["route"])
                value = int(sample.value)
                counts[key] = counts.get(key, 0) + value
                cls = _status_class(labels.get("status", ""))
                status_classes[cls] = status_classes.get(cls, 0) + value
                # 4xx and 5xx both count as errors: a 401 storm and a 500
                # storm are both things an operator wants to see here.
                if cls >= 4:
                    errors[key] = errors.get(key, 0) + value
            elif sample.name == f"{_LATENCY_METRIC}_sum":
                latency_sums[(labels["method"], labels["route"])] = sample.value
            elif sample.name == f"{_LATENCY_METRIC}_count":
                latency_counts[(labels["method"], labels["route"])] = sample.value
            elif sample.name == f"{_LATENCY_METRIC}_bucket":
                key = (labels["method"], labels["route"])
                latency_buckets.setdefault(key, []).append(
                    (float(labels["le"]), sample.value)
                )

    routes: list[RouteUsage] = []
    for key, request_count in counts.items():
        method, route = key
        error_count = errors.get(key, 0)
        observed = latency_counts.get(key, 0.0)
        avg_ms = (latency_sums.get(key, 0.0) / observed * 1000) if observed > 0 else None
        p95 = _percentile_from_buckets(latency_buckets.get(key, []), observed)
        routes.append(
            RouteUsage(
                method=method,
                route=route,
                requests=request_count,
                errors=error_count,
                error_rate=(error_count / request_count) if request_count else 0.0,
                avg_latency_ms=avg_ms,
                p95_latency_ms=(p95 * 1000) if p95 is not None else None,
            )
        )

    # Busiest first - the default question this page answers is "what is
    # this API actually serving?", and the table is sortable client-side
    # for the others.
    routes.sort(key=lambda r: r.requests, reverse=True)

    total_requests = sum(counts.values())
    total_errors = sum(errors.values())
    total_observed = sum(latency_counts.values())
    total_latency = sum(latency_sums.values())

    all_buckets: dict[float, float] = {}
    for bucket_list in latency_buckets.values():
        for upper, cumulative in bucket_list:
            all_buckets[upper] = all_buckets.get(upper, 0.0) + cumulative
    overall_p95 = _percentile_from_buckets(list(all_buckets.items()), total_observed)

    return ApiUsageSnapshot(
        total_requests=total_requests,
        total_errors=total_errors,
        error_rate=(total_errors / total_requests) if total_requests else 0.0,
        avg_latency_ms=(total_latency / total_observed * 1000) if total_observed > 0 else None,
        p95_latency_ms=(overall_p95 * 1000) if overall_p95 is not None else None,
        route_count=len(routes),
        status_2xx=status_classes.get(2, 0),
        status_3xx=status_classes.get(3, 0),
        status_4xx=status_classes.get(4, 0),
        status_5xx=status_classes.get(5, 0),
        routes=routes,
    )


__all__ = ["ApiUsageSnapshot", "RouteUsage", "build_snapshot"]

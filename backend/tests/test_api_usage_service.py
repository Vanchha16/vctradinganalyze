"""Unit tests for the Prometheus->JSON fold behind `GET /admin/api-usage`
(ADR-144). Each builds its own `CollectorRegistry` rather than touching
the global one - otherwise these would depend on whatever requests other
tests happened to push through `MetricsMiddleware` first."""

from prometheus_client import CollectorRegistry, Counter, Histogram

from app.services.api_usage_service import build_snapshot


def _registry() -> tuple[CollectorRegistry, Counter, Histogram]:
    registry = CollectorRegistry()
    counter = Counter(
        "http_requests_total",
        "Total HTTP requests received, labeled by method/route template/status.",
        ["method", "route", "status"],
        registry=registry,
    )
    histogram = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds, labeled by method/route template.",
        ["method", "route"],
        registry=registry,
    )
    return registry, counter, histogram


def test_empty_registry_reports_zeroes_not_a_crash() -> None:
    """A freshly restarted process has no samples at all - the page must
    render, not 500."""
    registry, _, _ = _registry()

    snapshot = build_snapshot(registry)

    assert snapshot.total_requests == 0
    assert snapshot.total_errors == 0
    assert snapshot.error_rate == 0.0
    assert snapshot.avg_latency_ms is None
    assert snapshot.p95_latency_ms is None
    assert snapshot.routes == []


def test_counts_and_error_rate_fold_across_status_codes() -> None:
    """One `(method, route)` pair spans several status labels; requests
    sum across them and 4xx/5xx both count as errors."""
    registry, counter, _ = _registry()
    counter.labels(method="GET", route="/signals", status="200").inc(8)
    counter.labels(method="GET", route="/signals", status="404").inc(1)
    counter.labels(method="GET", route="/signals", status="500").inc(1)

    snapshot = build_snapshot(registry)

    assert snapshot.total_requests == 10
    assert snapshot.total_errors == 2  # 404 + 500, not just the 500
    assert snapshot.error_rate == 0.2
    (route,) = snapshot.routes
    assert (route.method, route.route) == ("GET", "/signals")
    assert route.requests == 10
    assert route.errors == 2
    assert route.error_rate == 0.2


def test_status_class_tiles_are_split_by_first_digit() -> None:
    registry, counter, _ = _registry()
    counter.labels(method="GET", route="/a", status="200").inc(3)
    counter.labels(method="GET", route="/a", status="301").inc(1)
    counter.labels(method="GET", route="/a", status="401").inc(2)
    counter.labels(method="GET", route="/a", status="503").inc(4)

    snapshot = build_snapshot(registry)

    assert (snapshot.status_2xx, snapshot.status_3xx) == (3, 1)
    assert (snapshot.status_4xx, snapshot.status_5xx) == (2, 4)


def test_average_latency_is_reported_in_milliseconds() -> None:
    registry, counter, histogram = _registry()
    counter.labels(method="GET", route="/assets", status="200").inc(2)
    histogram.labels(method="GET", route="/assets").observe(0.010)
    histogram.labels(method="GET", route="/assets").observe(0.030)

    snapshot = build_snapshot(registry)

    (route,) = snapshot.routes
    assert route.avg_latency_ms is not None
    assert round(route.avg_latency_ms, 3) == 20.0  # mean of 10ms and 30ms


def test_p95_ignores_a_single_slow_outlier() -> None:
    """The whole point of reporting p95 rather than max: 1 slow request
    in 20 is exactly the 5% the percentile discards, so p95 stays in the
    fast bucket. If this ever starts returning the outlier's bucket, the
    percentile maths has broken."""
    registry, counter, histogram = _registry()
    counter.labels(method="GET", route="/mostly-fast", status="200").inc(20)
    for _ in range(19):
        histogram.labels(method="GET", route="/mostly-fast").observe(0.001)
    histogram.labels(method="GET", route="/mostly-fast").observe(2.0)

    snapshot = build_snapshot(registry)

    (route,) = snapshot.routes
    assert route.p95_latency_ms is not None
    assert route.p95_latency_ms <= 10.0  # the 1ms cluster's bucket, not 2s


def test_p95_reflects_a_genuinely_slow_tail() -> None:
    """When a real share of traffic is slow (20% here, well past the 5%
    the percentile discards), p95 must land in the slow bucket - this is
    the case that makes the column worth showing at all."""
    registry, counter, histogram = _registry()
    counter.labels(method="GET", route="/slow", status="200").inc(20)
    for _ in range(16):
        histogram.labels(method="GET", route="/slow").observe(0.001)
    for _ in range(4):
        histogram.labels(method="GET", route="/slow").observe(1.5)

    snapshot = build_snapshot(registry)

    (route,) = snapshot.routes
    assert route.p95_latency_ms is not None
    assert route.p95_latency_ms >= 1000.0


def test_p95_is_none_when_the_percentile_falls_in_the_inf_bucket() -> None:
    """Everything slower than the largest finite bucket has no meaningful
    upper bound to report - `None` is honest, a made-up number is not."""
    registry, counter, histogram = _registry()
    counter.labels(method="GET", route="/glacial", status="200").inc(3)
    for _ in range(3):
        histogram.labels(method="GET", route="/glacial").observe(120.0)

    snapshot = build_snapshot(registry)

    (route,) = snapshot.routes
    assert route.p95_latency_ms is None
    assert route.avg_latency_ms is not None  # the mean still works


def test_routes_are_sorted_busiest_first() -> None:
    registry, counter, _ = _registry()
    counter.labels(method="GET", route="/quiet", status="200").inc(2)
    counter.labels(method="GET", route="/busy", status="200").inc(50)
    counter.labels(method="GET", route="/middling", status="200").inc(9)

    snapshot = build_snapshot(registry)

    assert [r.route for r in snapshot.routes] == ["/busy", "/middling", "/quiet"]
    assert snapshot.route_count == 3


def test_unmatched_bucket_is_surfaced_like_any_other_route() -> None:
    """ADR-136 collapses unrouted paths into `"unmatched"`; a spike there
    is a scan/probe signal, so the page must not filter it out."""
    registry, counter, _ = _registry()
    counter.labels(method="POST", route="unmatched", status="404").inc(17)

    snapshot = build_snapshot(registry)

    (route,) = snapshot.routes
    assert route.route == "unmatched"
    assert route.requests == 17
    assert route.error_rate == 1.0


def test_route_with_counts_but_no_latency_observations_reports_none() -> None:
    """Defensive: the counter and histogram are incremented separately in
    the middleware, so a snapshot taken between them must not divide by
    zero."""
    registry, counter, _ = _registry()
    counter.labels(method="GET", route="/counted-only", status="200").inc(5)

    snapshot = build_snapshot(registry)

    (route,) = snapshot.routes
    assert route.requests == 5
    assert route.avg_latency_ms is None
    assert route.p95_latency_ms is None

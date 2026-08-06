"""Phase 9D (ADR-136) - `GET /metrics`. Structured like
`tests/test_rate_limit.py`/`tests/test_quota.py`: a minimal custom
FastAPI app wired the same way `app.main.app` is (the real metrics
middleware/route mounted under the real API prefix), rather than
importing the full app with its unrelated business-logic dependencies
(DB, auth).

`app/middleware/metrics.py`'s `Counter`/`Histogram` are module-level
singletons registered once in `prometheus_client`'s default global
registry - they persist across every test in the process, including
ones in other test files that exercise `app.main.app` directly (e.g.
`test_health.py`). Assertions here read a metric's value before acting
and compare the delta, rather than asserting an absolute count, so
ordering relative to the rest of the suite never matters.
"""

from typing import Annotated

import pytest
from fastapi import APIRouter, FastAPI, Path
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from prometheus_client.parser import text_string_to_metric_families

from app.config import settings
from app.exceptions import register_exception_handlers
from app.middleware.metrics import MetricsMiddleware


def _sample(metric_name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(metric_name, labels) or 0.0


@pytest.fixture
def metrics_client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(MetricsMiddleware)

    router = APIRouter()

    @router.get("/metrics-test-widgets/{widget_id}")
    def _widget(widget_id: Annotated[str, Path()]) -> dict[str, str]:
        return {"id": widget_id}

    app.include_router(router, prefix=settings.api_v1_prefix)

    from app.api.v1.routes import metrics as metrics_route

    app.include_router(metrics_route.router, prefix=settings.api_v1_prefix)

    return TestClient(app)


# --- Access control (fail-closed) --------------------------------------------


def test_returns_404_when_no_token_configured(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "metrics_auth_token", "")

    response = metrics_client.get("/api/v1/metrics")

    assert response.status_code == 404


def test_returns_404_with_missing_token_when_one_is_configured(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "metrics_auth_token", "secret-token")

    response = metrics_client.get("/api/v1/metrics")

    assert response.status_code == 404


def test_returns_404_with_wrong_token_when_one_is_configured(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "metrics_auth_token", "secret-token")

    response = metrics_client.get(
        "/api/v1/metrics", headers={"Authorization": "Bearer wrong-token"}
    )

    assert response.status_code == 404


def test_returns_prometheus_text_with_the_correct_token(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "metrics_auth_token", "secret-token")

    response = metrics_client.get(
        "/api/v1/metrics", headers={"Authorization": "Bearer secret-token"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    # The parser normalizes counter family names by stripping the "_total"
    # suffix (OpenMetrics convention) - the exposed sample name is still
    # "http_requests_total", as REGISTRY.get_sample_value() elsewhere in
    # this file confirms.
    families = {family.name for family in text_string_to_metric_families(response.text)}
    assert "http_requests" in families
    assert "http_request_duration_seconds" in families


# --- Request instrumentation --------------------------------------------------


def test_request_counters_increment_across_requests(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "metrics_auth_token", "secret-token")
    route = "/metrics-test-widgets/{widget_id}"
    before = _sample("http_requests_total", method="GET", route=route, status="200")

    metrics_client.get("/api/v1/metrics-test-widgets/abc")
    metrics_client.get("/api/v1/metrics-test-widgets/xyz")

    after = _sample("http_requests_total", method="GET", route=route, status="200")
    assert after == before + 2


def test_two_different_path_params_collapse_into_one_series(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cardinality guard - the most important test in this file.
    Two requests to the same route template with different path params
    (`EURUSD`, `XAUUSD`-style symbols in production) must land on ONE
    time series, not two, or metrics become an unbounded-memory hazard
    on the 911MB production box (BACKLOG.md §10)."""
    monkeypatch.setattr(settings, "metrics_auth_token", "secret-token")
    route = "/metrics-test-widgets/{widget_id}"
    before = _sample("http_requests_total", method="GET", route=route, status="200")

    metrics_client.get("/api/v1/metrics-test-widgets/EURUSD")
    metrics_client.get("/api/v1/metrics-test-widgets/XAUUSD")

    response = metrics_client.get(
        "/api/v1/metrics", headers={"Authorization": "Bearer secret-token"}
    )
    after = _sample("http_requests_total", method="GET", route=route, status="200")

    assert after == before + 2, "two distinct path params must sum into one series"
    assert "EURUSD" not in response.text
    assert "XAUUSD" not in response.text

    families = list(text_string_to_metric_families(response.text))
    request_count_family = next(f for f in families if f.name == "http_requests")
    matching_series = [
        sample
        for sample in request_count_family.samples
        if sample.name == "http_requests_total"
        and sample.labels.get("route") == route
        and sample.labels.get("status") == "200"
    ]
    assert len(matching_series) == 1, "exactly one series for this route+status, not one per symbol"


def test_metrics_does_not_appear_in_its_own_output(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "metrics_auth_token", "secret-token")
    headers = {"Authorization": "Bearer secret-token"}

    metrics_client.get("/api/v1/metrics", headers=headers)
    metrics_client.get("/api/v1/metrics", headers=headers)
    response = metrics_client.get("/api/v1/metrics", headers=headers)

    metrics_route = "/metrics"
    assert _sample("http_requests_total", method="GET", route=metrics_route, status="200") == 0.0
    assert 'route="/metrics"' not in response.text


def test_metrics_is_not_rate_limited(
    metrics_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No rate-limit dependency is attached to the metrics router at all
    (`app/api/v1/router.py`) - a burst well past 9A's public tiers (20-100
    req/60s) must still return 200 every time."""
    monkeypatch.setattr(settings, "metrics_auth_token", "secret-token")
    headers = {"Authorization": "Bearer secret-token"}

    responses = [metrics_client.get("/api/v1/metrics", headers=headers) for _ in range(150)]

    assert all(response.status_code == 200 for response in responses)

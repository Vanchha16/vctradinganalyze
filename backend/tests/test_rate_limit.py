"""Phase 9A (ADR-132) - per-IP rate limiting for the public,
unauthenticated route modules. Structured like `tests/test_quota.py`
(Phase 9, ADR-127): direct dependency-function tests plus end-to-end
tests through the real exception handler and a real router-level
`include_router(..., dependencies=[...])` wiring, since that's how this
limiter is actually applied (`app/api/v1/router.py`), unlike `quota.py`'s
per-handler `Depends()`.
"""

from typing import Any

import pytest
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.dependencies.rate_limit import rate_limit_public
from app.exceptions import QuotaExceededException, register_exception_handlers


class FakeRedis:
    """Minimal in-memory stand-in for the two Redis calls
    `rate_limit_public` makes (`incr`, `expire`) - same shape as
    `test_quota.py`'s `FakeRedis`."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key: str, seconds: int) -> None:
        pass

    def expire_window(self, key: str) -> None:
        """Test helper simulating the fixed window rolling over."""
        self.counts.pop(key, None)


class RaisingRedis:
    """Simulates a Redis outage - every call raises."""

    def incr(self, key: str) -> int:
        raise ConnectionError("redis unreachable")

    def expire(self, key: str, seconds: int) -> None:
        raise ConnectionError("redis unreachable")


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr("app.dependencies.rate_limit._redis_client", fake)
    return fake


def _make_request(client_host: str | None) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "client": (client_host, 12345) if client_host is not None else None,
        "headers": [],
    }
    return Request(scope)


# --- rate_limit_public (direct) ----------------------------------------------


def test_allows_requests_under_the_limit(fake_redis: FakeRedis) -> None:
    check = rate_limit_public("public_data", limit=3, window_seconds=60)
    request = _make_request("1.2.3.4")

    for _ in range(3):
        check(request)  # must not raise


def test_raises_once_the_limit_is_hit(fake_redis: FakeRedis) -> None:
    check = rate_limit_public("public_data", limit=2, window_seconds=60)
    request = _make_request("1.2.3.4")

    check(request)
    check(request)
    with pytest.raises(QuotaExceededException):
        check(request)


def test_window_resets_the_counter(fake_redis: FakeRedis) -> None:
    check = rate_limit_public("public_data", limit=1, window_seconds=60)
    request = _make_request("1.2.3.4")

    check(request)
    with pytest.raises(QuotaExceededException):
        check(request)

    fake_redis.expire_window("ratelimit:public_data:1.2.3.4")

    check(request)  # must not raise


def test_fails_open_when_redis_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """The most important test: a Redis outage must never take the public
    site down."""
    monkeypatch.setattr("app.dependencies.rate_limit._redis_client", RaisingRedis())
    check = rate_limit_public("public_data", limit=0, window_seconds=60)
    request = _make_request("1.2.3.4")

    check(request)  # must not raise
    check(request)


def test_limit_is_per_ip(fake_redis: FakeRedis) -> None:
    check = rate_limit_public("public_data", limit=1, window_seconds=60)
    request_a = _make_request("1.1.1.1")
    request_b = _make_request("2.2.2.2")

    check(request_a)
    with pytest.raises(QuotaExceededException):
        check(request_a)

    # IP B's budget is untouched by IP A's usage.
    check(request_b)


def test_buckets_are_independent(fake_redis: FakeRedis) -> None:
    engine_check = rate_limit_public("public_engine", limit=1, window_seconds=60)
    data_check = rate_limit_public("public_data", limit=1, window_seconds=60)
    request = _make_request("1.2.3.4")

    engine_check(request)
    with pytest.raises(QuotaExceededException):
        engine_check(request)

    # The data-tier budget is unaffected by the engine tier's usage.
    data_check(request)


def test_missing_client_falls_back_to_a_shared_unknown_bucket(fake_redis: FakeRedis) -> None:
    """`request.client` can be `None` for a raw ASGI caller - must not
    crash, though such callers necessarily share one budget."""
    check = rate_limit_public("public_data", limit=1, window_seconds=60)
    request = _make_request(None)

    check(request)
    with pytest.raises(QuotaExceededException):
        check(request)


# --- End-to-end through a real router (mirrors app/api/v1/router.py) --------


@pytest.fixture
def rate_limited_test_client(fake_redis: FakeRedis) -> TestClient:
    """Proves the dependency works the way it's actually wired in
    `app/api/v1/router.py` - attached via `include_router(...,
    dependencies=[...])`, not per-handler - and that exceeding it returns
    a real `429` with the standard envelope."""
    app = FastAPI()
    register_exception_handlers(app)

    router = APIRouter()

    @router.get("/guarded")
    def _guarded() -> dict[str, str]:
        return {"status": "ok"}

    limiter = Depends(rate_limit_public("public_data", limit=1, window_seconds=60))
    app.include_router(router, dependencies=[limiter])

    health_router = APIRouter()

    @health_router.get("/health")
    def _health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(health_router)

    return TestClient(app, client=("9.9.9.9", 12345))


def test_guarded_route_allows_the_first_request(rate_limited_test_client: TestClient) -> None:
    response = rate_limited_test_client.get("/guarded")

    assert response.status_code == 200


def test_guarded_route_returns_429_with_standard_envelope_once_over_limit(
    rate_limited_test_client: TestClient,
) -> None:
    rate_limited_test_client.get("/guarded")
    response = rate_limited_test_client.get("/guarded")

    assert response.status_code == 429
    assert response.json()["error"] == "quota_exceeded"
    assert "message" in response.json()


def test_health_is_never_rate_limited_even_once_the_public_budget_is_exhausted(
    rate_limited_test_client: TestClient,
) -> None:
    rate_limited_test_client.get("/guarded")
    rate_limited_test_client.get("/guarded")  # exhausts the budget for this IP

    response = rate_limited_test_client.get("/health")

    assert response.status_code == 200

"""Phase 9 (ADR-127) - per-user quota on the two LLM-token-spending
endpoints. Structured like `tests/test_rbac.py` (Phase 8B): direct
dependency-function tests plus one end-to-end test through the real
exception handler."""

import uuid
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.dependencies.auth import get_current_user
from app.dependencies.quota import require_quota
from app.exceptions import QuotaExceededException, register_exception_handlers
from app.models.enums import UserRole
from app.models.user import User


def _make_user(role: UserRole = UserRole.REGISTERED) -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        username="user",
        password_hash=hash_password("Correct-Horse9"),
        role=role,
    )


class FakeRedis:
    """Minimal in-memory stand-in for the two Redis calls `require_quota`
    makes (`incr`, `expire`). No real TTL enforcement - `expire_window`
    simulates a window rolling over by dropping the key, the same
    observable effect as a real Redis TTL firing."""

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
    monkeypatch.setattr("app.dependencies.quota._redis_client", fake)
    return fake


# --- require_quota (direct) --------------------------------------------------


def test_allows_requests_under_the_limit(fake_redis: FakeRedis) -> None:
    check = require_quota("ai_analysis", limit=3, window_seconds=3600)
    user = _make_user()

    for _ in range(3):
        assert check(current_user=user) is user


def test_raises_quota_exceeded_once_limit_is_hit(fake_redis: FakeRedis) -> None:
    check = require_quota("ai_analysis", limit=2, window_seconds=3600)
    user = _make_user()

    check(current_user=user)
    check(current_user=user)
    with pytest.raises(QuotaExceededException):
        check(current_user=user)


def test_window_resets_the_counter(fake_redis: FakeRedis) -> None:
    check = require_quota("ai_analysis", limit=1, window_seconds=3600)
    user = _make_user()

    check(current_user=user)
    with pytest.raises(QuotaExceededException):
        check(current_user=user)

    # Simulate the fixed window expiring in Redis.
    fake_redis.expire_window(f"quota:ai_analysis:{user.id}")

    assert check(current_user=user) is user


def test_fails_open_when_redis_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """The most important test: a Redis outage must never block the AI
    endpoints. The request is allowed through even far past any limit."""
    monkeypatch.setattr("app.dependencies.quota._redis_client", RaisingRedis())
    check = require_quota("ai_analysis", limit=0, window_seconds=3600)
    user = _make_user()

    assert check(current_user=user) is user
    assert check(current_user=user) is user


def test_quota_is_per_user(fake_redis: FakeRedis) -> None:
    check = require_quota("ai_analysis", limit=1, window_seconds=3600)
    user_a = _make_user()
    user_b = _make_user()

    check(current_user=user_a)
    with pytest.raises(QuotaExceededException):
        check(current_user=user_a)

    # User B's budget is untouched by user A's usage.
    assert check(current_user=user_b) is user_b


def test_buckets_are_independent(fake_redis: FakeRedis) -> None:
    analysis_check = require_quota("ai_analysis", limit=1, window_seconds=3600)
    chat_check = require_quota("ai_chat", limit=1, window_seconds=3600)
    user = _make_user()

    analysis_check(current_user=user)
    with pytest.raises(QuotaExceededException):
        analysis_check(current_user=user)

    # Chat budget is unaffected by AI-analysis spend.
    assert chat_check(current_user=user) is user


def test_no_role_is_exempt(fake_redis: FakeRedis) -> None:
    """Explicit product decision: even Super Admin is subject to the
    quota - there is no role bypass (ADR-127)."""
    check = require_quota("ai_analysis", limit=1, window_seconds=3600)
    admin = _make_user(UserRole.SUPER_ADMIN)

    check(current_user=admin)
    with pytest.raises(QuotaExceededException):
        check(current_user=admin)


# --- End-to-end through the real exception handler --------------------------


@pytest.fixture
def quota_test_client(fake_redis: FakeRedis) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    check = require_quota("ai_analysis", limit=1, window_seconds=3600)

    @app.get("/quota-guarded")
    def _quota_guarded(user: User = Depends(check)) -> dict[str, Any]:  # noqa: B008
        return {"email": user.email}

    return TestClient(app)


def test_quota_guarded_route_allows_first_request(quota_test_client: TestClient) -> None:
    user = _make_user()
    quota_test_client.app.dependency_overrides[get_current_user] = lambda: user

    response = quota_test_client.get("/quota-guarded")

    assert response.status_code == 200


def test_quota_guarded_route_returns_429_with_standard_envelope(
    quota_test_client: TestClient,
) -> None:
    user = _make_user()
    quota_test_client.app.dependency_overrides[get_current_user] = lambda: user

    quota_test_client.get("/quota-guarded")
    response = quota_test_client.get("/quota-guarded")

    assert response.status_code == 429
    assert response.json()["error"] == "quota_exceeded"
    assert "message" in response.json()

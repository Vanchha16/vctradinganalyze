"""Unit tests for ingestion health tracking (Phase 9G, ADR-139) - a fake
Redis-shaped client, no real Redis dependency, matching
`test_redis_fixed_window.py`'s spirit for the shared quota/rate_limit helper."""

import pytest

from app.services import ingestion_health


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def set(self, key: str, value: str) -> None:
        self._store[key] = value.encode()

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class _RaisingRedis:
    def get(self, key: str) -> None:
        raise ConnectionError("simulated redis outage")

    def set(self, key: str, value: str) -> None:
        raise ConnectionError("simulated redis outage")

    def delete(self, key: str) -> None:
        raise ConnectionError("simulated redis outage")


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(ingestion_health, "_redis_client", fake)
    return fake


def test_record_success_then_get_health_reports_it() -> None:
    ingestion_health.record_success("news")

    status = ingestion_health.get_health("news", providers=["mock"], uses_mock=True)

    assert status.last_success_at is not None
    assert status.last_error is None
    assert status.providers == ["mock"]
    assert status.uses_mock is True


def test_record_failure_then_get_health_reports_the_error() -> None:
    ingestion_health.record_failure("news", "every provider failed: mock: boom")

    status = ingestion_health.get_health("news", providers=["mock"], uses_mock=True)

    assert status.last_error == "every provider failed: mock: boom"


def test_record_success_clears_a_previous_error() -> None:
    ingestion_health.record_failure("news", "boom")
    ingestion_health.record_success("news")

    status = ingestion_health.get_health("news", providers=["mock"], uses_mock=True)

    assert status.last_error is None
    assert status.last_success_at is not None


def test_get_health_never_recorded_returns_none_fields() -> None:
    status = ingestion_health.get_health(
        "economic_calendar", providers=["mock"], uses_mock=True
    )

    assert status.last_success_at is None
    assert status.last_error is None


def test_get_health_fails_open_when_redis_read_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingestion_health, "_redis_client", _RaisingRedis())

    status = ingestion_health.get_health("news", providers=["mock"], uses_mock=True)

    assert status.last_success_at is None
    assert status.last_error is None
    assert status.providers == ["mock"]


def test_record_success_fails_open_when_redis_write_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ingestion_health, "_redis_client", _RaisingRedis())

    ingestion_health.record_success("news")  # must not raise


def test_record_failure_fails_open_when_redis_write_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ingestion_health, "_redis_client", _RaisingRedis())

    ingestion_health.record_failure("news", "boom")  # must not raise


def test_pipelines_have_independent_health_keys() -> None:
    ingestion_health.record_success("news")
    ingestion_health.record_failure("economic_calendar", "calendar broke")

    news_status = ingestion_health.get_health("news", providers=["mock"], uses_mock=True)
    calendar_status = ingestion_health.get_health(
        "economic_calendar", providers=["mock"], uses_mock=True
    )

    assert news_status.last_success_at is not None
    assert news_status.last_error is None
    assert calendar_status.last_success_at is None
    assert calendar_status.last_error == "calendar broke"

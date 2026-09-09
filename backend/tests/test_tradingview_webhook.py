"""Tests for the inbound TradingView webhook (ADR-146).

This is the only unauthenticated-by-session surface in the project that
writes to the database, so the auth boundary gets the most coverage
here: an unset secret, a wrong secret and a nonexistent route must be
indistinguishable from the outside.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.base import Base
from app.dependencies.database import get_db
from app.main import app
from app.models.tradingview_alert import TradingViewAlert

_SECRET = "test-webhook-secret"
_URL = f"/api/v1/webhooks/tradingview/{_SECRET}"
_PAYLOAD = {
    "symbol": "XAUUSD",
    "exchange": "OANDA",
    "timeframe": "60",
    "direction": "sell",
    "score": 72.5,
    "entry": 4384.62,
    "time": "2026-09-09T01:00:00Z",
    "source": "technical_heuristic_only",
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    # StaticPool + check_same_thread=False: `TestClient` runs the handler
    # in a threadpool, and the default SingletonThreadPool would hand that
    # thread a *different* in-memory database with no tables in it. Same
    # fixture shape as `test_admin_system_api.py`.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[TradingViewAlert.__table__])
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    def override_get_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    # Delivery is best-effort and asynchronous; these tests are about the
    # HTTP boundary and persistence, not Celery.
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_tradingview_alert_delivery", lambda _id: None
    )
    monkeypatch.setattr(settings, "tradingview_webhook_secret", _SECRET)

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.engine = engine  # type: ignore[attr-defined]
        test_client.factory = factory  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()


def test_valid_alert_is_accepted_and_persisted(client: TestClient) -> None:
    response = client.post(_URL, json=_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

    with client.factory() as session:  # type: ignore[attr-defined]
        alert = session.query(TradingViewAlert).one()
        assert alert.symbol == "XAUUSD"
        assert alert.direction == "sell"
        assert alert.exchange == "OANDA"
        assert alert.timeframe == "60"  # kept verbatim, not mapped to Timeframe
        assert alert.source == "technical_heuristic_only"
        assert alert.raw_payload["symbol"] == "XAUUSD"
        # Never delivered synchronously - that is the async task's job.
        assert alert.delivered_at is None


def test_wrong_secret_is_404_and_stores_nothing(client: TestClient) -> None:
    """404, not 403: the route must not confirm it exists to a caller
    without the secret."""
    response = client.post("/api/v1/webhooks/tradingview/not-the-secret", json=_PAYLOAD)

    assert response.status_code == 404
    with client.factory() as session:  # type: ignore[attr-defined]
        assert session.query(TradingViewAlert).count() == 0


def test_unset_secret_disables_the_route_entirely(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default. An empty secret means the webhook was never
    deliberately enabled, so even the "correct" empty token is refused -
    otherwise every deployment would ship an open write endpoint."""
    monkeypatch.setattr(settings, "tradingview_webhook_secret", "")

    assert client.post(_URL, json=_PAYLOAD).status_code == 404
    assert client.post("/api/v1/webhooks/tradingview/", json=_PAYLOAD).status_code in (404, 405)

    with client.factory() as session:  # type: ignore[attr-defined]
        assert session.query(TradingViewAlert).count() == 0


def test_direction_is_normalized_but_still_constrained(client: TestClient) -> None:
    """Hand-edited TradingView templates produce "BUY", " Buy " and the
    like; those are accepted. Anything that is not buy/sell is not."""
    assert client.post(_URL, json={**_PAYLOAD, "direction": " BUY "}).status_code == 200
    assert client.post(_URL, json={**_PAYLOAD, "direction": "long"}).status_code == 422

    with client.factory() as session:  # type: ignore[attr-defined]
        alert = session.query(TradingViewAlert).one()
        assert alert.direction == "buy"


def test_minimal_payload_is_accepted(client: TestClient) -> None:
    """Only symbol and direction are required - a partially-filled alert
    is still evidence of what arrived, and rejecting it would hide a
    misconfigured template."""
    response = client.post(_URL, json={"symbol": "EURUSD", "direction": "buy"})

    assert response.status_code == 200
    with client.factory() as session:  # type: ignore[attr-defined]
        alert = session.query(TradingViewAlert).one()
        assert alert.entry_price is None
        assert alert.score is None
        assert alert.alert_time is None


def test_missing_required_fields_are_rejected(client: TestClient) -> None:
    assert client.post(_URL, json={"direction": "buy"}).status_code == 422
    assert client.post(_URL, json={"symbol": "XAUUSD"}).status_code == 422


def test_oversized_symbol_is_rejected_before_the_database(client: TestClient) -> None:
    """The column is String(32); the schema bound stops an oversized value
    reaching it rather than relying on the database to complain."""
    response = client.post(_URL, json={**_PAYLOAD, "symbol": "X" * 64})

    assert response.status_code == 422
    with client.factory() as session:  # type: ignore[attr-defined]
        assert session.query(TradingViewAlert).count() == 0


def test_duplicate_alerts_are_both_stored(client: TestClient) -> None:
    """TradingView re-fires alerts. There is no unique constraint by
    design - the fact that a duplicate arrived is itself information, and
    silently dropping it would hide a misconfigured alert."""
    client.post(_URL, json=_PAYLOAD)
    client.post(_URL, json=_PAYLOAD)

    with client.factory() as session:  # type: ignore[attr-defined]
        assert session.query(TradingViewAlert).count() == 2


def test_alert_never_creates_a_signal(client: TestClient) -> None:
    """The core safety property of ADR-146: an inbound alert is recorded
    and notified, never turned into a tradeable signal. `signals` is not
    even created in this test's schema, so any attempt to write one would
    raise rather than pass silently."""
    assert client.post(_URL, json=_PAYLOAD).status_code == 200

    with client.factory() as session:  # type: ignore[attr-defined]
        assert session.query(TradingViewAlert).count() == 1

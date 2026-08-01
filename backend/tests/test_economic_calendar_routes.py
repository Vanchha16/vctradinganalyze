import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_db
from app.main import app
from app.models.economic_event import EconomicEvent
from app.models.enums import EconomicEventCategory, EconomicEventImportance, EconomicEventStatus

_TABLES = [EconomicEvent.__table__]


@pytest.fixture
def session_engine() -> Generator[object, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    yield engine


@pytest.fixture
def client(session_engine: object) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = Session(session_engine)  # type: ignore[arg-type]
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def session(session_engine: object) -> Generator[Session, None, None]:
    with Session(session_engine) as session:  # type: ignore[arg-type]
        yield session


def _seed(session: Session, **overrides: object) -> EconomicEvent:
    defaults: dict[str, object] = {
        "country": "US",
        "currency": "USD",
        "event_name": "CPI y/y",
        "category": EconomicEventCategory.INFLATION,
        "importance": EconomicEventImportance.CRITICAL,
        "forecast": Decimal("3.2"),
        "previous": Decimal("3.5"),
        "actual": Decimal("2.8"),
        "surprise": Decimal("-0.4"),
        "unit": "%",
        "status": EconomicEventStatus.RELEASED,
        "source": "mock",
        "release_time": datetime.now(UTC),
    }
    defaults.update(overrides)
    event = EconomicEvent(**defaults)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def test_list_calendar_events_returns_paginated_items(client: TestClient, session: Session) -> None:
    _seed(session)

    response = client.get("/api/v1/calendar")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["event_name"] == "CPI y/y"
    assert body["items"][0]["market_bias"] is not None


def test_list_calendar_events_filters_by_currency(client: TestClient, session: Session) -> None:
    _seed(session, currency="USD")
    _seed(session, currency="EUR", event_name="ECB Rate Decision")

    response = client.get("/api/v1/calendar", params={"currency": "EUR"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["currency"] == "EUR"


def test_list_calendar_events_filters_by_importance(client: TestClient, session: Session) -> None:
    _seed(session, importance=EconomicEventImportance.CRITICAL)
    _seed(
        session,
        event_name="Building Permits",
        category=EconomicEventCategory.HOUSING,
        importance=EconomicEventImportance.MEDIUM,
    )

    response = client.get("/api/v1/calendar", params={"importance": "medium"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_calendar_events_pagination(client: TestClient, session: Session) -> None:
    for i in range(3):
        _seed(session, event_name=f"Event {i}", release_time=datetime.now(UTC) + timedelta(hours=i))

    response = client.get("/api/v1/calendar", params={"page": 1, "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_get_calendar_event_detail(client: TestClient, session: Session) -> None:
    event = _seed(session)

    response = client.get(f"/api/v1/calendar/{event.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["event_name"] == "CPI y/y"
    assert Decimal(body["surprise"]) == Decimal("-0.4")


def test_get_calendar_event_404_for_unknown_id(client: TestClient, session: Session) -> None:
    response = client.get(f"/api/v1/calendar/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_upcoming_only_returns_critical_and_high(client: TestClient, session: Session) -> None:
    now = datetime.now(UTC)
    _seed(
        session,
        event_name="GDP q/q",
        category=EconomicEventCategory.GROWTH,
        importance=EconomicEventImportance.CRITICAL,
        actual=None,
        surprise=None,
        status=EconomicEventStatus.SCHEDULED,
        release_time=now + timedelta(hours=1),
    )
    _seed(
        session,
        event_name="Trade Balance",
        category=EconomicEventCategory.OTHER,
        importance=EconomicEventImportance.MEDIUM,
        actual=None,
        surprise=None,
        status=EconomicEventStatus.SCHEDULED,
        release_time=now + timedelta(hours=2),
    )

    response = client.get("/api/v1/calendar/upcoming")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["event_name"] == "GDP q/q"


def test_calendar_routes_require_no_authentication(client: TestClient, session: Session) -> None:
    _seed(session)

    response = client.get("/api/v1/calendar")

    assert response.status_code == 200


def test_upcoming_route_is_not_shadowed_by_id_route(client: TestClient, session: Session) -> None:
    """`/calendar/upcoming` must resolve to the dedicated route, not be
    parsed as a UUID path parameter for `/calendar/{event_id}`."""
    response = client.get("/api/v1/calendar/upcoming")

    assert response.status_code == 200

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.economic_event import EconomicEvent
from app.models.enums import (
    EconomicEventCategory,
    EconomicEventImportance,
    EconomicEventStatus,
)
from app.repositories.economic_event_repository import EconomicEventRepository
from app.services.economic_calendar_engine import EconomicCalendarEngine

_TABLES = [EconomicEvent.__table__]


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _make_event(
    session: Session,
    *,
    event_name: str = "CPI y/y",
    country: str = "US",
    currency: str = "USD",
    category: EconomicEventCategory = EconomicEventCategory.INFLATION,
    importance: EconomicEventImportance = EconomicEventImportance.CRITICAL,
    release_time: datetime,
    actual: Decimal | None = None,
    forecast: Decimal | None = Decimal("3.2"),
    surprise: Decimal | None = None,
    status: EconomicEventStatus = EconomicEventStatus.SCHEDULED,
) -> EconomicEvent:
    event = EconomicEvent(
        country=country,
        currency=currency,
        event_name=event_name,
        category=category,
        importance=importance,
        forecast=forecast,
        previous=Decimal("3.5"),
        actual=actual,
        surprise=surprise,
        unit="%",
        status=status,
        source="mock",
        release_time=release_time,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def test_list_events_returns_all_when_no_filters(session: Session) -> None:
    now = datetime.now(UTC)
    _make_event(session, release_time=now)
    engine = EconomicCalendarEngine(EconomicEventRepository(session))

    result, total = engine.list_events()

    assert total == 1
    assert len(result.events) == 1


def test_list_events_filters_by_currency(session: Session) -> None:
    now = datetime.now(UTC)
    _make_event(session, currency="USD", release_time=now)
    _make_event(session, currency="EUR", event_name="ECB Rate Decision", release_time=now)
    engine = EconomicCalendarEngine(EconomicEventRepository(session))

    result, total = engine.list_events(currency="EUR")

    assert total == 1
    assert result.events[0].currency == "EUR"


def test_list_events_filters_by_date_range(session: Session) -> None:
    now = datetime.now(UTC)
    _make_event(session, release_time=now - timedelta(days=10))
    _make_event(session, event_name="GDP q/q", release_time=now + timedelta(days=1))
    engine = EconomicCalendarEngine(EconomicEventRepository(session))

    result, total = engine.list_events(start=now, end=now + timedelta(days=5))

    assert total == 1
    assert result.events[0].event_name == "GDP q/q"


def test_get_upcoming_only_returns_critical_and_high(session: Session) -> None:
    now = datetime.now(UTC)
    _make_event(
        session,
        event_name="Building Permits",
        category=EconomicEventCategory.HOUSING,
        importance=EconomicEventImportance.MEDIUM,
        release_time=now + timedelta(hours=1),
    )
    _make_event(
        session,
        event_name="GDP q/q",
        category=EconomicEventCategory.GROWTH,
        importance=EconomicEventImportance.CRITICAL,
        release_time=now + timedelta(hours=2),
    )
    engine = EconomicCalendarEngine(EconomicEventRepository(session))

    result = engine.get_upcoming()

    assert len(result.events) == 1
    assert result.events[0].event_name == "GDP q/q"


def test_get_by_id_returns_none_for_unknown_id(session: Session) -> None:
    engine = EconomicCalendarEngine(EconomicEventRepository(session))
    assert engine.get_by_id(uuid.uuid4()) is None


def test_risk_window_is_computed_not_read_from_db(session: Session) -> None:
    now = datetime.now(UTC)
    event = _make_event(
        session,
        importance=EconomicEventImportance.CRITICAL,
        release_time=now + timedelta(minutes=10),
    )
    engine = EconomicCalendarEngine(EconomicEventRepository(session))

    evidence = engine.get_by_id(event.id)

    assert evidence is not None
    assert evidence.risk_window is True  # within Critical's +-30min window


def test_market_bias_is_none_until_actual_known(session: Session) -> None:
    now = datetime.now(UTC)
    event = _make_event(session, actual=None, release_time=now)
    engine = EconomicCalendarEngine(EconomicEventRepository(session))

    evidence = engine.get_by_id(event.id)

    assert evidence is not None
    assert evidence.market_bias is None


def test_market_bias_is_computed_once_actual_known(session: Session) -> None:
    now = datetime.now(UTC)
    event = _make_event(
        session,
        actual=Decimal("2.8"),
        surprise=Decimal("-0.4"),
        status=EconomicEventStatus.RELEASED,
        release_time=now,
    )
    engine = EconomicCalendarEngine(EconomicEventRepository(session))

    evidence = engine.get_by_id(event.id)

    assert evidence is not None
    assert evidence.market_bias is not None
    assert "currency" in evidence.market_bias

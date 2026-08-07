from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.economic_event import EconomicEvent
from app.models.enums import EconomicEventStatus
from app.repositories.economic_event_repository import EconomicEventRepository
from app.services.economic_calendar.providers.base import RawEconomicEvent
from app.services.economic_calendar.providers.exceptions import (
    AllEconomicCalendarProvidersFailedError,
    TransientEconomicCalendarProviderError,
)
from app.services.economic_calendar.providers.mock import MockEconomicCalendarProvider
from app.services.economic_calendar_ingestion_pipeline import EconomicCalendarIngestionPipeline

_TABLES = [EconomicEvent.__table__]
_RELEASE = datetime(2026, 1, 1, tzinfo=UTC)


class _StubProvider:
    """A hand-rolled provider returning a controlled event sequence
    across calls, so upsert/revision behavior (ADR-058) can be tested
    deterministically without depending on real wall-clock time."""

    name = "stub"

    def __init__(self, sequence: list[list[RawEconomicEvent]]) -> None:
        self._sequence = sequence
        self._call_count = 0

    def fetch_events(self, start: datetime, end: datetime) -> list[RawEconomicEvent]:
        events = self._sequence[min(self._call_count, len(self._sequence) - 1)]
        self._call_count += 1
        return events


class _FailingProvider:
    name = "failing"

    def fetch_events(self, start: datetime, end: datetime) -> list[RawEconomicEvent]:
        raise TransientEconomicCalendarProviderError("simulated outage")


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _scheduled_event() -> RawEconomicEvent:
    return RawEconomicEvent(
        country="US",
        currency="USD",
        event_name="CPI y/y",
        release_time=_RELEASE,
        source_name="stub",
        forecast=Decimal("3.2"),
        previous=Decimal("3.5"),
        actual=None,
        unit="%",
    )


def test_run_persists_events_from_mock_provider(session: Session) -> None:
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[MockEconomicCalendarProvider()],
        event_repository=EconomicEventRepository(session),
    )
    now = datetime.now(UTC)

    result = pipeline.run(now - timedelta(days=7), now + timedelta(days=30))

    assert result.created > 0
    assert result.updated == 0  # first run, nothing pre-existing
    rows = session.execute(select(EconomicEvent)).scalars().all()
    assert len(rows) == result.created


def test_run_creates_scheduled_event_with_no_actual(session: Session) -> None:
    provider = _StubProvider([[_scheduled_event()]])
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[provider], event_repository=EconomicEventRepository(session)
    )

    result = pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))

    assert (result.created, result.updated) == (1, 0)
    row = session.execute(select(EconomicEvent)).scalar_one()
    assert row.status == EconomicEventStatus.SCHEDULED
    assert row.actual is None
    assert row.surprise is None


def test_run_twice_upserts_the_same_event_on_release(session: Session) -> None:
    """Second fetch reports `actual` for the same natural key - the
    existing row must be updated in place, not duplicated (ADR-058)."""
    released_event = RawEconomicEvent(
        country="US",
        currency="USD",
        event_name="CPI y/y",
        release_time=_RELEASE,
        source_name="stub",
        forecast=Decimal("3.2"),
        previous=Decimal("3.5"),
        actual=Decimal("2.8"),
        unit="%",
    )
    provider = _StubProvider([[_scheduled_event()], [released_event]])
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[provider], event_repository=EconomicEventRepository(session)
    )

    first = pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))
    second = pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))

    assert (first.created, first.updated) == (1, 0)
    assert (second.created, second.updated) == (0, 1)
    rows = session.execute(select(EconomicEvent)).scalars().all()
    assert len(rows) == 1  # upserted, not duplicated
    row = rows[0]
    assert row.status == EconomicEventStatus.RELEASED
    assert row.actual == Decimal("2.8")
    assert row.surprise == Decimal("-0.4")


def test_run_marks_status_revised_when_actual_changes_after_release(session: Session) -> None:
    first_release = RawEconomicEvent(
        country="US",
        currency="USD",
        event_name="CPI y/y",
        release_time=_RELEASE,
        source_name="stub",
        forecast=Decimal("3.2"),
        previous=Decimal("3.5"),
        actual=Decimal("2.8"),
        unit="%",
    )
    revised = RawEconomicEvent(
        country="US",
        currency="USD",
        event_name="CPI y/y",
        release_time=_RELEASE,
        source_name="stub",
        forecast=Decimal("3.2"),
        previous=Decimal("3.5"),
        actual=Decimal("2.9"),  # revised actual value
        unit="%",
    )
    provider = _StubProvider([[first_release], [revised]])
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[provider], event_repository=EconomicEventRepository(session)
    )

    pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))
    pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))

    row = session.execute(select(EconomicEvent)).scalar_one()
    assert row.status == EconomicEventStatus.REVISED
    assert row.actual == Decimal("2.9")


def test_run_does_not_transition_status_when_actual_unchanged(session: Session) -> None:
    same_release = RawEconomicEvent(
        country="US",
        currency="USD",
        event_name="CPI y/y",
        release_time=_RELEASE,
        source_name="stub",
        forecast=Decimal("3.2"),
        previous=Decimal("3.5"),
        actual=Decimal("2.8"),
        unit="%",
    )
    provider = _StubProvider([[same_release], [same_release]])
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[provider], event_repository=EconomicEventRepository(session)
    )

    pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))
    pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))

    row = session.execute(select(EconomicEvent)).scalar_one()
    assert row.status == EconomicEventStatus.RELEASED  # not REVISED - value didn't change


def test_run_categorizes_and_scores_importance_on_ingestion(session: Session) -> None:
    provider = _StubProvider([[_scheduled_event()]])
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[provider], event_repository=EconomicEventRepository(session)
    )

    pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))

    row = session.execute(select(EconomicEvent)).scalar_one()
    assert row.category.value == "inflation"
    assert row.importance.value == "critical"  # CPI is a docs/14 §4 Critical example


def test_run_continues_when_one_provider_fails(session: Session) -> None:
    provider = _StubProvider([[_scheduled_event()]])
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[_FailingProvider(), provider],
        event_repository=EconomicEventRepository(session),
    )

    result = pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))

    assert (result.created, result.updated) == (1, 0)
    outcomes_by_provider = {o.provider: o for o in result.provider_outcomes}
    assert outcomes_by_provider["failing"].success is False
    assert outcomes_by_provider["stub"].success is True


# --- Phase 9G: failure distinguishability (ADR-139) ------------------------


def test_run_raises_when_every_provider_fails(session: Session) -> None:
    """§3/§8's regression test - a total provider failure must not look
    like a clean, empty success."""
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[_FailingProvider()], event_repository=EconomicEventRepository(session)
    )

    with pytest.raises(AllEconomicCalendarProvidersFailedError):
        pipeline.run(_RELEASE - timedelta(days=1), _RELEASE + timedelta(days=1))


def test_provider_names_and_uses_mock(session: Session) -> None:
    pipeline = EconomicCalendarIngestionPipeline(
        providers=[MockEconomicCalendarProvider()],
        event_repository=EconomicEventRepository(session),
    )

    assert pipeline.provider_names == ["mock"]
    assert pipeline.uses_mock is True

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, SMCEventStatus, SMCEventType, Timeframe
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository

_TABLES = [Asset.__table__, SMCEvent.__table__, SMCProcessingState.__table__]


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


@pytest.fixture
def asset(session: Session) -> Asset:
    asset = Asset(symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def test_smc_event_defaults_to_active_status(session: Session, asset: Asset) -> None:
    repo = SMCEventRepository(session)
    event = repo.create(
        SMCEvent(
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            event_type=SMCEventType.BOS,
            price=Decimal("1.1"),
            detected_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    session.commit()

    assert event.status == SMCEventStatus.ACTIVE


def test_update_status_mutates_row_in_place(session: Session, asset: Asset) -> None:
    """Unlike every other append-only table, smc_events rows are mutable
    (ADR-033) - the same row transitions lifecycle states rather than a
    new row being inserted."""
    repo = SMCEventRepository(session)
    event = repo.create(
        SMCEvent(
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            event_type=SMCEventType.ORDER_BLOCK_BULLISH,
            price=Decimal("1.1"),
            detected_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    session.commit()
    event_id = event.id

    repo.update_status(event, SMCEventStatus.MITIGATED)
    session.commit()

    assert repo.get_by_id(event_id).status == SMCEventStatus.MITIGATED
    assert repo._count(repo._query()) == 1  # still one row, not a new one


def test_list_active_filters_by_status_and_type(session: Session, asset: Asset) -> None:
    repo = SMCEventRepository(session)
    active = repo.create(
        SMCEvent(
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            event_type=SMCEventType.ORDER_BLOCK_BULLISH,
            price=Decimal("1.1"),
            detected_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    mitigated = repo.create(
        SMCEvent(
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            event_type=SMCEventType.ORDER_BLOCK_BULLISH,
            price=Decimal("1.2"),
            detected_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
    )
    session.commit()
    repo.update_status(mitigated, SMCEventStatus.MITIGATED)
    session.commit()

    active_events = repo.list_active(asset.id, Timeframe.H1)

    assert [e.id for e in active_events] == [active.id]


def test_get_by_natural_key_finds_existing_zone(session: Session, asset: Asset) -> None:
    repo = SMCEventRepository(session)
    detected_at = datetime(2026, 1, 1, tzinfo=UTC)
    repo.create(
        SMCEvent(
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            event_type=SMCEventType.FAIR_VALUE_GAP_BULLISH,
            price=Decimal("1.1"),
            detected_at=detected_at,
        )
    )
    session.commit()

    found = repo.get_by_natural_key(
        asset.id, Timeframe.H1, SMCEventType.FAIR_VALUE_GAP_BULLISH, detected_at
    )
    missing = repo.get_by_natural_key(
        asset.id, Timeframe.H1, SMCEventType.FAIR_VALUE_GAP_BEARISH, detected_at
    )

    assert found is not None
    assert missing is None


def test_smc_events_are_never_deleted_by_asset_cascade_but_row_persists_via_status(
    session: Session, asset: Asset
) -> None:
    """Sanity check that archiving is a status change, not a delete -
    the row count is unaffected by transitioning through every lifecycle
    state (ADR-037)."""
    repo = SMCEventRepository(session)
    event = repo.create(
        SMCEvent(
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            event_type=SMCEventType.LIQUIDITY_SWEEP,
            price=Decimal("1.1"),
            detected_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    session.commit()

    for status in (SMCEventStatus.MITIGATED, SMCEventStatus.ARCHIVED):
        repo.update_status(event, status)
        session.commit()

    assert repo._count(repo._query()) == 1
    assert repo.get_by_id(event.id).status == SMCEventStatus.ARCHIVED


def test_processing_state_upsert_inserts_then_updates(session: Session, asset: Asset) -> None:
    repo = SMCProcessingStateRepository(session)
    first = repo.upsert(
        asset.id,
        Timeframe.H1,
        last_processed_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        engine_version="1.0.0",
    )
    session.commit()

    updated = repo.upsert(
        asset.id,
        Timeframe.H1,
        last_processed_timestamp=datetime(2026, 1, 2, tzinfo=UTC),
        engine_version="1.0.1",
    )
    session.commit()

    assert updated.id == first.id
    assert updated.engine_version == "1.0.1"
    assert repo._count(repo._query()) == 1

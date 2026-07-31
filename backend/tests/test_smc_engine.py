import math
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.exceptions import ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import MarketType, SMCEventStatus, Timeframe
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.models.smc_processing_state import SMCProcessingState
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.smc.types import Direction, OrderBlockEvidence
from app.services.smc_engine import SMCEngine, _archive_stale_order_blocks

_TABLES = [
    Asset.__table__,
    PriceCandle.__table__,
    SMCEvent.__table__,
    SMCProcessingState.__table__,
]


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


def _seed_candles(session: Session, asset: Asset, timeframe: Timeframe, count: int) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(count):
        mid = 100 + 0.3 * i + math.sin(2 * math.pi * i / 24) * 5
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=timeframe,
                timestamp=base + timedelta(hours=i),
                open=Decimal(str(mid)),
                high=Decimal(str(mid + 1)),
                low=Decimal(str(mid - 1)),
                close=Decimal(str(mid)),
                volume=Decimal(str(1000 + i)),
            )
        )
    session.commit()


def _make_engine(session: Session) -> SMCEngine:
    return SMCEngine(
        PriceCandleRepository(session),
        SMCEventRepository(session),
        SMCProcessingStateRepository(session),
    )


def test_analyze_raises_when_no_candles(session: Session, asset: Asset) -> None:
    engine = _make_engine(session)

    with pytest.raises(ResourceNotFoundException):
        engine.analyze(asset, Timeframe.H1)


def test_analyze_warns_on_insufficient_candles(session: Session, asset: Asset) -> None:
    _seed_candles(session, asset, Timeframe.H1, 5)
    engine = _make_engine(session)

    result = engine.analyze(asset, Timeframe.H1)

    assert any("candles available" in w for w in result.warnings)


def test_analyze_persists_and_updates_processing_state(session: Session, asset: Asset) -> None:
    _seed_candles(session, asset, Timeframe.H1, 300)
    engine = _make_engine(session)

    engine.analyze(asset, Timeframe.H1)

    state_repo = SMCProcessingStateRepository(session)
    state = state_repo.get_for_asset_timeframe(asset.id, Timeframe.H1)
    assert state is not None
    assert state.engine_version == "1.0.0"


def test_analyze_is_idempotent_across_repeated_calls(session: Session, asset: Asset) -> None:
    _seed_candles(session, asset, Timeframe.H1, 300)
    engine = _make_engine(session)

    engine.analyze(asset, Timeframe.H1)
    event_repo = SMCEventRepository(session)
    first_count = event_repo._count(event_repo._query())

    engine.analyze(asset, Timeframe.H1)
    second_count = event_repo._count(event_repo._query())

    assert first_count > 0
    assert first_count == second_count


def test_archive_stale_order_blocks_transitions_after_threshold() -> None:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    ob = OrderBlockEvidence(
        direction=Direction.BULLISH,
        zone_high=Decimal("12"),
        zone_low=Decimal("10"),
        created_at=created_at,
        status=SMCEventStatus.MITIGATED,
        touched=True,
        mitigated=True,
        broken=False,
        strength_score=0.5,
        freshness_score=0.1,
        volume_confirmed=False,
    )

    _archive_stale_order_blocks([ob], created_at + timedelta(days=31))

    assert ob.status == SMCEventStatus.ARCHIVED


def test_archive_stale_order_blocks_leaves_recent_zones_alone() -> None:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    ob = OrderBlockEvidence(
        direction=Direction.BULLISH,
        zone_high=Decimal("12"),
        zone_low=Decimal("10"),
        created_at=created_at,
        status=SMCEventStatus.MITIGATED,
        touched=True,
        mitigated=True,
        broken=False,
        strength_score=0.5,
        freshness_score=0.1,
        volume_confirmed=False,
    )

    _archive_stale_order_blocks([ob], created_at + timedelta(days=1))

    assert ob.status == SMCEventStatus.MITIGATED

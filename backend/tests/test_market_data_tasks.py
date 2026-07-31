from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.indicator_result import IndicatorResult
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.repositories.price_candle_repository import PriceCandleRepository
from app.workers import market_data_tasks

_TABLES = [Asset.__table__, PriceCandle.__table__, IndicatorResult.__table__, SMCEvent.__table__]


@pytest.fixture
def session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    monkeypatch.setattr(market_data_tasks, "SessionLocal", factory)
    yield factory


def test_register_market_data_schedule_has_one_entry_per_timeframe() -> None:
    schedule = market_data_tasks.register_market_data_schedule()

    assert len(schedule) == len(Timeframe)
    for entry in schedule.values():
        assert entry["task"] == "market_data.collect_for_timeframe"


def test_collect_market_data_task_persists_candles_for_active_assets(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        session.add(Asset(symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX))
        session.add(
            Asset(
                symbol="INACTIVE",
                name="Inactive Asset",
                market_type=MarketType.FOREX,
                is_active=False,
            )
        )
        session.commit()

    market_data_tasks.collect_market_data_task(Timeframe.M1.value)

    with session_factory() as session:
        repo = PriceCandleRepository(session)
        assert repo._count(repo._query()) > 0

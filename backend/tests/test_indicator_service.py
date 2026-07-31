import math
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.indicator_result import IndicatorResult
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.repositories.indicator_result_repository import IndicatorResultRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.indicator_service import IndicatorService

_TABLES = [Asset.__table__, PriceCandle.__table__, IndicatorResult.__table__, SMCEvent.__table__]


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


def _seed_candles(session: Session, asset: Asset, count: int) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(count):
        price = Decimal("100") + Decimal(str(math.sin(i / 10) * 5))
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=base + timedelta(minutes=i),
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=Decimal(str(1000 + i)),
            )
        )
    session.commit()


def test_calculate_and_store_with_no_candles_returns_empty(session: Session, asset: Asset) -> None:
    service = IndicatorService(PriceCandleRepository(session), IndicatorResultRepository(session))
    assert service.calculate_and_store(asset.id, Timeframe.M1) == []


def test_calculate_and_store_persists_results_for_every_indicator(
    session: Session, asset: Asset
) -> None:
    _seed_candles(session, asset, 260)
    service = IndicatorService(PriceCandleRepository(session), IndicatorResultRepository(session))

    results = service.calculate_and_store(asset.id, Timeframe.M1)
    session.commit()

    assert len(results) > 0
    names = {r.indicator for r in results}
    assert "rsi_14" in names
    assert "macd" in names
    assert "adx_14" in names

    repo = IndicatorResultRepository(session)
    stored = repo.list_for_asset_timeframe(asset.id, Timeframe.M1, limit=100)
    assert len(stored) == len(results)


def test_calculate_and_store_skips_indicators_with_insufficient_data(
    session: Session, asset: Asset
) -> None:
    _seed_candles(session, asset, 5)  # far too little history for most indicators
    service = IndicatorService(PriceCandleRepository(session), IndicatorResultRepository(session))

    results = service.calculate_and_store(asset.id, Timeframe.M1)

    names = {r.indicator for r in results}
    assert "rsi_14" not in names
    assert "sma_200" not in names

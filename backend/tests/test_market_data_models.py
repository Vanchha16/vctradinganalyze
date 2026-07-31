from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.indicator_result import IndicatorResult
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.repositories.asset_repository import AssetRepository
from app.repositories.indicator_result_repository import IndicatorResultRepository
from app.repositories.price_candle_repository import PriceCandleRepository

_TABLES = [Asset.__table__, PriceCandle.__table__, IndicatorResult.__table__, SMCEvent.__table__]


def _sqlite_engine_with_fk_enforcement() -> Engine:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = _sqlite_engine_with_fk_enforcement()
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _make_asset(session: Session, **overrides: object) -> Asset:
    defaults: dict[str, object] = {
        "symbol": "EURUSD",
        "name": "Euro / US Dollar",
        "market_type": MarketType.FOREX,
        "base_currency": "EUR",
        "quote_currency": "USD",
    }
    defaults.update(overrides)
    asset = Asset(**defaults)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def test_asset_defaults(session: Session) -> None:
    asset = _make_asset(session)
    assert asset.is_active is True


def test_asset_repository_lookups(session: Session) -> None:
    _make_asset(session)
    repo = AssetRepository(session)

    assert repo.get_by_symbol("EURUSD") is not None
    assert repo.get_by_symbol("NOPE") is None
    assert len(repo.list_active()) == 1


def test_asset_symbol_is_unique(session: Session) -> None:
    _make_asset(session)
    with pytest.raises(IntegrityError):
        session.add(Asset(symbol="EURUSD", name="Dup", market_type=MarketType.FOREX))
        session.flush()


def test_price_candle_unique_constraint(session: Session) -> None:
    asset = _make_asset(session)
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    session.add(
        PriceCandle(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            timestamp=timestamp,
            open=Decimal("1.1"),
            high=Decimal("1.2"),
            low=Decimal("1.0"),
            close=Decimal("1.15"),
        )
    )
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=timestamp,
                open=Decimal("1.1"),
                high=Decimal("1.2"),
                low=Decimal("1.0"),
                close=Decimal("1.16"),
            )
        )
        session.flush()


def test_price_candle_cascade_delete(session: Session) -> None:
    asset = _make_asset(session)
    session.add(
        PriceCandle(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal("1.1"),
            high=Decimal("1.2"),
            low=Decimal("1.0"),
            close=Decimal("1.15"),
        )
    )
    session.commit()

    session.delete(asset)
    session.commit()

    repo = PriceCandleRepository(session)
    assert repo._count(repo._query()) == 0


def test_price_candle_repository_upsert_inserts_then_updates(session: Session) -> None:
    asset = _make_asset(session)
    repo = PriceCandleRepository(session)
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    first = repo.upsert(
        PriceCandle(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            timestamp=timestamp,
            open=Decimal("1.1"),
            high=Decimal("1.2"),
            low=Decimal("1.0"),
            close=Decimal("1.15"),
        )
    )
    session.commit()
    assert repo._count(repo._query()) == 1

    updated = repo.upsert(
        PriceCandle(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            timestamp=timestamp,
            open=Decimal("1.1"),
            high=Decimal("1.3"),
            low=Decimal("1.0"),
            close=Decimal("1.25"),
        )
    )
    session.commit()

    assert repo._count(repo._query()) == 1  # still one row, not a duplicate
    assert updated.id == first.id
    assert updated.close == Decimal("1.25")


def test_price_candle_repository_list_range_and_latest(session: Session) -> None:
    asset = _make_asset(session)
    repo = PriceCandleRepository(session)
    base = datetime(2026, 1, 1, tzinfo=UTC)

    for i in range(5):
        repo.upsert(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=base + timedelta(minutes=i),
                open=Decimal("1.1"),
                high=Decimal("1.2"),
                low=Decimal("1.0"),
                close=Decimal("1.15"),
            )
        )
    session.commit()

    # SQLite returns naive datetimes for DateTime(timezone=True) columns
    # (BACKLOG.md §9) - normalize before comparing against tz-aware values.
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

    latest = repo.get_latest(asset.id, Timeframe.M1)
    assert latest is not None
    assert _aware(latest.timestamp) == base + timedelta(minutes=4)

    ranged = repo.list_range(asset.id, Timeframe.M1, start=base, end=base + timedelta(minutes=2))
    assert [_aware(c.timestamp) for c in ranged] == [
        base,
        base + timedelta(minutes=1),
        base + timedelta(minutes=2),
    ]

    recent = repo.list_recent(asset.id, Timeframe.M1, limit=2)
    assert [_aware(c.timestamp) for c in recent] == [
        base + timedelta(minutes=3),
        base + timedelta(minutes=4),
    ]


def test_indicator_result_repository(session: Session) -> None:
    asset = _make_asset(session)
    repo = IndicatorResultRepository(session)

    repo.create(
        IndicatorResult(
            asset_id=asset.id,
            timeframe=Timeframe.M1,
            indicator="rsi_14",
            value=Decimal("55.5"),
            context={"note": "test"},
        )
    )
    session.commit()

    results = repo.list_for_asset_timeframe(asset.id, Timeframe.M1)
    assert len(results) == 1
    assert results[0].indicator == "rsi_14"

    filtered = repo.list_for_asset_timeframe(asset.id, Timeframe.M1, indicator="macd")
    assert filtered == []


def test_indicator_result_survives_asset_deletion_is_not_the_case_cascade(session: Session) -> None:
    """indicator_results has ondelete=CASCADE (docs/03 relationships), unlike
    audit_logs' SET NULL - deleting the asset removes its indicator history."""
    asset = _make_asset(session)
    repo = IndicatorResultRepository(session)
    repo.create(
        IndicatorResult(
            asset_id=asset.id, timeframe=Timeframe.M1, indicator="rsi_14", value=Decimal("50")
        )
    )
    session.commit()

    session.delete(asset)
    session.commit()

    assert repo._count(repo._query()) == 0

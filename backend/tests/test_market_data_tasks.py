from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
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


# --- Phase 9H (ADR-140): collection cadence floor + quota projection ---


def test_build_beat_schedule_seconds_floors_only_timeframes_shorter_than_it() -> None:
    schedule = market_data_tasks.build_beat_schedule_seconds(400.0)

    # Shorter than the floor: raised to the floor.
    assert schedule[Timeframe.M1] == 400.0
    assert schedule[Timeframe.M5] == 400.0
    # Already longer than the floor: unaffected.
    assert schedule[Timeframe.M15] == 900.0
    assert schedule[Timeframe.M30] == 1800.0
    assert schedule[Timeframe.H1] == 3600.0
    assert schedule[Timeframe.H4] == 14400.0
    assert schedule[Timeframe.D1] == 86400.0


def test_build_beat_schedule_seconds_changing_floor_changes_schedule() -> None:
    low_floor = market_data_tasks.build_beat_schedule_seconds(60.0)
    high_floor = market_data_tasks.build_beat_schedule_seconds(600.0)

    assert low_floor[Timeframe.M1] == 60.0
    assert high_floor[Timeframe.M1] == 600.0
    assert low_floor[Timeframe.M15] == high_floor[Timeframe.M15] == 900.0


def test_market_data_min_collection_interval_seconds_default_is_300() -> None:
    """Guards the default deliberately - a future edit to this value should
    be a conscious choice, not an accidental one (Phase 9H spec §6)."""
    assert settings.market_data_min_collection_interval_seconds == 300.0


def test_projected_daily_requests_per_asset_matches_the_floored_schedule() -> None:
    """Computed independently from `BEAT_SCHEDULE_SECONDS` (module-level,
    built from the real default floor) across *all nine* `Timeframe`
    values - not just the six the build spec's own table enumerated (it
    omitted M30/W1/MN). See the report-back note on this discrepancy."""
    expected = sum(
        86_400 / interval for interval in market_data_tasks.BEAT_SCHEDULE_SECONDS.values()
    )
    assert market_data_tasks.projected_daily_requests_per_asset() == pytest.approx(expected)
    # Sanity-check against the floored per-timeframe run counts directly.
    assert market_data_tasks.projected_daily_requests_per_asset() == pytest.approx(
        288 + 288 + 96 + 48 + 24 + 6 + 1 + (86_400 / 604_800) + (86_400 / 2_592_000)
    )


class _RecordingLogger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict[str, object]]] = []
        self.infos: list[tuple[str, dict[str, object]]] = []

    def warning(self, event: str, **kwargs: object) -> None:
        self.warnings.append((event, kwargs))

    def info(self, event: str, **kwargs: object) -> None:
        self.infos.append((event, kwargs))


def test_log_quota_projection_warns_when_projection_exceeds_the_daily_cap(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_factory() as session:
        session.add(Asset(symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX))
        session.add(Asset(symbol="XAUUSD", name="Gold / US Dollar", market_type=MarketType.METAL))
        session.commit()

    recorder = _RecordingLogger()
    monkeypatch.setattr(market_data_tasks, "logger", recorder)
    monkeypatch.setattr(settings, "market_data_rate_limits_per_day", {"twelve_data": 800.0})

    market_data_tasks.log_quota_projection()

    assert len(recorder.warnings) == 1
    event, fields = recorder.warnings[0]
    assert event == "market_data.quota_projection_exceeds_limit"
    assert fields["provider"] == "twelve_data"
    assert fields["active_asset_count"] == 2
    assert not recorder.infos


def test_log_quota_projection_does_not_warn_when_projection_is_under_the_cap(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_factory() as session:
        session.add(Asset(symbol="EURUSD", name="Euro / US Dollar", market_type=MarketType.FOREX))
        session.commit()

    recorder = _RecordingLogger()
    monkeypatch.setattr(market_data_tasks, "logger", recorder)
    monkeypatch.setattr(settings, "market_data_rate_limits_per_day", {"twelve_data": 800.0})

    market_data_tasks.log_quota_projection()

    assert not recorder.warnings
    assert len(recorder.infos) == 1
    assert recorder.infos[0][0] == "market_data.quota_projection"

from collections.abc import Generator
from datetime import timedelta

import pytest
from celery.schedules import crontab
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


def test_h1_and_m15_are_collected_just_after_their_candles_close() -> None:
    """ADR-166 - signal generation (minute 3) and M15 confirmation (3, 18, 33,
    48) must read the candle that just closed, not one up to an interval old."""
    schedule = market_data_tasks.register_market_data_schedule()

    h1 = schedule["collect-market-data-h1"]["schedule"]
    m15 = schedule["collect-market-data-m15"]["schedule"]
    assert isinstance(h1, crontab)
    assert h1.minute == {1}
    assert isinstance(m15, crontab)
    assert m15.minute == {1, 16, 31, 46}
    # M5 and H4 are aligned too (audit D9, next test); the rest keep intervals.
    for timeframe in (Timeframe.M1, Timeframe.M30, Timeframe.D1, Timeframe.W1, Timeframe.MN):
        interval = market_data_tasks.BEAT_SCHEDULE_SECONDS[timeframe]
        assert schedule[f"collect-market-data-{timeframe.value}"]["schedule"] == interval


def test_m5_and_h4_are_collected_three_minutes_after_their_candles_close() -> None:
    """Audit D9: the first run after the close plus Twelve Data's ~2-minute
    publication lag holds the final bar; the SMC path waits for it."""
    schedule = market_data_tasks.register_market_data_schedule()

    m5 = schedule["collect-market-data-m5"]["schedule"]
    assert isinstance(m5, crontab)
    assert m5.minute == set(range(3, 60, 5))
    assert m5.hour == set(range(24))

    h4 = schedule["collect-market-data-h4"]["schedule"]
    assert isinstance(h4, crontab)
    assert h4.minute == {3}
    # Summer (01, 05, ...) and winter (00, 04, ...) H4 boundaries both covered.
    assert h4.hour == {0, 1, 4, 5, 8, 9, 12, 13, 16, 17, 20, 21}


def test_the_smc_run_follows_the_m5_collection_by_one_minute() -> None:
    from app.workers import smc_tasks

    run = smc_tasks.register_smc_schedule()["smc-run"]["schedule"]
    assert isinstance(run, crontab)
    assert run.minute == set(range(4, 60, 5))


def test_an_operator_override_keeps_its_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "market_data_collection_interval_overrides", {"M15": 600.0})

    assert market_data_tasks.schedule_for(Timeframe.M15, 600.0) == 600.0


def test_a_raised_floor_keeps_its_interval() -> None:
    """A floor above the candle length is a quota decision the alignment must
    not quietly override."""
    assert market_data_tasks.schedule_for(Timeframe.M15, 1200.0) == 1200.0


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


# --- ADR-171: collection windows overlap between runs ---


def test_every_collection_window_spans_several_runs() -> None:
    """A window no longer than the time between runs loses every candle the
    provider has not published yet when a run happens - production lost about
    40% of M1 candles this way on the 300s floor."""
    for timeframe, interval in market_data_tasks.BEAT_SCHEDULE_SECONDS.items():
        assert market_data_tasks.lookback_for(timeframe) >= timedelta(seconds=interval * 3)


def test_m1_on_a_slower_schedule_fetches_three_runs_back() -> None:
    interval = market_data_tasks.BEAT_SCHEDULE_SECONDS[Timeframe.M1]

    assert market_data_tasks.lookback_for(Timeframe.M1) == max(
        timedelta(minutes=5), timedelta(seconds=interval * 3)
    )


def test_timeframes_run_once_per_candle_keep_their_candle_based_window() -> None:
    assert market_data_tasks.lookback_for(Timeframe.H1) == timedelta(hours=5)


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
    omitted M30/W1/MN). See the report-back note on this discrepancy.

    Audit D9: counts what Beat really runs - H4 on its candle-close crontab
    runs at 12 boundary hours (summer and winter grids), not 6 intervals."""
    assert market_data_tasks.projected_daily_requests_per_asset() == pytest.approx(
        288 + 288 + 96 + 48 + 24 + 12 + 1 + (86_400 / 604_800) + (86_400 / 2_592_000)
    )
    # Still inside Twelve Data's free-tier cap for the one active asset.
    assert market_data_tasks.projected_daily_requests_per_asset() <= 800


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


def test_build_beat_schedule_applies_timeframe_overrides() -> None:
    """ADR-141: an override wins over both the timeframe's own duration
    and the ADR-140 floor - including going *faster* than the floor,
    which is the only lever on signal SL/TP detection latency."""
    schedule = market_data_tasks.build_beat_schedule_seconds(300.0, {"M1": 150.0, "m5": 1800.0})

    assert schedule[Timeframe.M1] == 150.0
    assert schedule[Timeframe.M5] == 1800.0  # lowercase key accepted too
    assert schedule[Timeframe.M15] == 900.0  # untouched, still duration-vs-floor


def test_build_beat_schedule_ignores_unknown_and_non_positive_overrides() -> None:
    """Operator-supplied config read at import time - a typo or a bad
    value must never stop the worker from starting."""
    schedule = market_data_tasks.build_beat_schedule_seconds(
        300.0, {"NOT_A_TIMEFRAME": 60.0, "M30": 0.0, "H1": -5.0}
    )

    assert schedule[Timeframe.M30] == 1800.0
    assert schedule[Timeframe.H1] == 3600.0
    assert len(schedule) == len(Timeframe)


def test_recommended_override_stays_within_twelve_data_daily_cap() -> None:
    """The concrete tuning ADR-141 recommends: M1 twice as fresh as the
    300s floor, paid for by slowing M5/M15/M30 - which the signal
    pipeline does not use for price monitoring - at no extra quota cost.
    Pinned as a test so a future edit can't silently reintroduce the
    2026-08-07 over-cap outage (ADR-140)."""
    seconds_per_day = 86_400
    schedule = market_data_tasks.build_beat_schedule_seconds(
        300.0, {"M1": 150.0, "M5": 1800.0, "M15": 1800.0, "M30": 1800.0}
    )
    projected = sum(seconds_per_day / interval for interval in schedule.values())

    assert projected <= 800  # Twelve Data free-tier daily cap
    assert schedule[Timeframe.M1] == 150.0

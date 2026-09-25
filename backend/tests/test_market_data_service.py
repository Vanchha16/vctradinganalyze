from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.indicator_result import IndicatorResult
from app.models.price_candle import PriceCandle
from app.models.smc_event import SMCEvent
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.exceptions import PermanentProviderError, TransientProviderError
from app.services.market_data.providers.base import ProviderCapabilities, RawCandle
from app.services.market_data.providers.mock import MockMarketDataProvider
from app.services.market_data_service import MarketDataService

_TABLES = [Asset.__table__, PriceCandle.__table__, IndicatorResult.__table__, SMCEvent.__table__]
_ALL_TIMEFRAMES_CAPABILITIES = ProviderCapabilities(
    supported_timeframes=frozenset(Timeframe),
    supported_market_types=frozenset(MarketType),
)


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


class _AlwaysFailingProvider:
    name = "always_failing"

    def __init__(self, error: Exception) -> None:
        self._error = error
        self.calls = 0

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        self.calls += 1
        raise self._error

    def health_check(self) -> bool:
        return False

    def capabilities(self) -> ProviderCapabilities:
        return _ALL_TIMEFRAMES_CAPABILITIES


class _FailsTwiceThenSucceedsProvider:
    name = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        self.calls += 1
        if self.calls < 3:
            raise TransientProviderError("temporary outage")
        return [
            RawCandle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=start,
                open=1.1,
                high=1.2,
                low=1.0,
                close=1.15,
            )
        ]

    def health_check(self) -> bool:
        return True

    def capabilities(self) -> ProviderCapabilities:
        return _ALL_TIMEFRAMES_CAPABILITIES


def _noop_sleep(_: float) -> None:
    return None


def test_collect_persists_valid_mock_candles(session: Session, asset: Asset) -> None:
    service = MarketDataService(
        providers=[MockMarketDataProvider()],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    end = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = end - timedelta(minutes=30)

    result = service.collect(asset, Timeframe.M1, start=start, end=end)

    assert result.fetched == 31
    assert result.persisted == 31
    assert result.rejected == 0

    repo = PriceCandleRepository(session)
    assert repo._count(repo._query()) == 31


def test_collect_is_idempotent_on_rerun(session: Session, asset: Asset) -> None:
    service = MarketDataService(
        providers=[MockMarketDataProvider()],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    end = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = end - timedelta(minutes=10)

    service.collect(asset, Timeframe.M1, start=start, end=end)
    session.commit()
    service.collect(asset, Timeframe.M1, start=start, end=end)
    session.commit()

    repo = PriceCandleRepository(session)
    assert repo._count(repo._query()) == 11  # no duplicates from re-running


def test_collect_retries_transient_errors_then_succeeds(session: Session, asset: Asset) -> None:
    flaky = _FailsTwiceThenSucceedsProvider()
    service = MarketDataService(
        providers=[flaky],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    end = datetime(2026, 1, 1, tzinfo=UTC)

    result = service.collect(asset, Timeframe.M1, start=end, end=end)

    assert flaky.calls == 3
    assert result.persisted == 1


def test_collect_gives_up_after_max_retry_attempts_and_falls_back(
    session: Session, asset: Asset
) -> None:
    always_failing = _AlwaysFailingProvider(TransientProviderError("down"))
    service = MarketDataService(
        providers=[always_failing],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    end = datetime(2026, 1, 1, tzinfo=UTC)

    result = service.collect(asset, Timeframe.M1, start=end, end=end)

    assert always_failing.calls == 3  # settings.market_data_retry_max_attempts default
    assert result.fetched == 0
    assert result.persisted == 0


def test_collect_fails_over_to_next_provider(session: Session, asset: Asset) -> None:
    failing = _AlwaysFailingProvider(PermanentProviderError("bad api key"))
    working = MockMarketDataProvider()
    service = MarketDataService(
        providers=[failing, working],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    end = datetime(2026, 1, 1, tzinfo=UTC)
    start = end - timedelta(minutes=5)

    result = service.collect(asset, Timeframe.M1, start=start, end=end)

    assert failing.calls == 1  # permanent error is not retried, moves on immediately
    assert result.persisted == 6


def test_collect_rejects_invalid_candles_without_failing_the_batch(
    session: Session, asset: Asset
) -> None:
    class _CorruptedProvider:
        name = "corrupted"

        def get_candles(
            self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
        ) -> list[RawCandle]:
            return [
                RawCandle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=start,
                    open=1.1,
                    high=0.5,  # corrupted: high below low
                    low=1.0,
                    close=1.15,
                ),
                RawCandle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=start + timedelta(minutes=1),
                    open=1.1,
                    high=1.2,
                    low=1.0,
                    close=1.15,
                ),
            ]

        def health_check(self) -> bool:
            return True

        def capabilities(self) -> ProviderCapabilities:
            return _ALL_TIMEFRAMES_CAPABILITIES

    service = MarketDataService(
        providers=[_CorruptedProvider()],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    end = datetime(2026, 1, 1, tzinfo=UTC)

    result = service.collect(asset, Timeframe.M1, start=end, end=end + timedelta(minutes=1))

    assert result.fetched == 2
    assert result.rejected == 1
    assert result.persisted == 1


def test_collect_skips_provider_that_declares_unsupported_timeframe(
    session: Session, asset: Asset
) -> None:
    class _M1OnlyProvider:
        name = "m1_only"

        def __init__(self) -> None:
            self.calls = 0

        def get_candles(
            self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
        ) -> list[RawCandle]:
            self.calls += 1
            return []

        def health_check(self) -> bool:
            return True

        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(
                supported_timeframes=frozenset({Timeframe.M1}),
                supported_market_types=frozenset(MarketType),
            )

    unsupported = _M1OnlyProvider()
    working = MockMarketDataProvider()
    service = MarketDataService(
        providers=[unsupported, working],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    end = datetime(2026, 1, 1, tzinfo=UTC)
    start = end - timedelta(minutes=5)

    result = service.collect(asset, Timeframe.H1, start=start, end=end)

    assert unsupported.calls == 0  # skipped proactively, never invoked
    assert result.persisted > 0  # fell through to the working provider


class _RecordingProvider:
    """Returns one candle and records when it was asked (audit D9)."""

    name = "recording"

    def __init__(self, close: float) -> None:
        self.close = close
        self.asked_at: list[datetime] = []

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        self.asked_at.append(datetime.now(UTC))
        return [
            RawCandle(
                symbol=symbol, timeframe=timeframe, timestamp=start,
                open=1.1, high=1.3, low=1.0, close=self.close,
            )
        ]

    def health_check(self) -> bool:
        return True

    def capabilities(self) -> ProviderCapabilities:
        return _ALL_TIMEFRAMES_CAPABILITIES


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)  # SQLite


def test_collect_stamps_fetched_at_no_later_than_the_provider_request(
    session: Session, asset: Asset
) -> None:
    """Audit D9: a candle is judged final by when it was fetched, so the
    stamp must never claim a moment later than the provider actually had."""
    provider = _RecordingProvider(close=1.2)
    service = MarketDataService(
        providers=[provider],
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(session),
        sleep=_noop_sleep,
    )
    before = datetime.now(UTC)
    end = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    service.collect(asset, Timeframe.M5, start=end - timedelta(minutes=5), end=end)

    row = session.query(PriceCandle).one()
    assert row.fetched_at is not None
    assert before <= _aware(row.fetched_at) <= provider.asked_at[0]


def test_a_refetch_rewrites_values_and_fetched_at(session: Session, asset: Asset) -> None:
    """The forming candle is stored and rewritten in place; the rewrite must
    carry its own fetch time, or a stale row would look final."""
    repo = PriceCandleRepository(session)
    t = datetime(2026, 9, 25, 5, tzinfo=UTC)
    first = datetime(2026, 9, 25, 5, 44, 33, tzinfo=UTC)
    later = datetime(2026, 9, 25, 9, 3, 10, tzinfo=UTC)
    for close, fetched_at in ((4274.86, first), (4294.52, later)):
        repo.upsert(PriceCandle(
            asset_id=asset.id, timeframe=Timeframe.H4, timestamp=t,
            open=4263.57, high=4296.09, low=4257.31, close=close, volume=None,
            fetched_at=fetched_at,
        ))
    row = session.query(PriceCandle).one()
    assert float(row.close) == 4294.52
    assert _aware(row.fetched_at) == later

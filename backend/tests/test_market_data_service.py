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
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.exceptions import PermanentProviderError, TransientProviderError
from app.services.market_data.providers.base import RawCandle
from app.services.market_data.providers.mock import MockMarketDataProvider
from app.services.market_data_service import MarketDataService

_TABLES = [Asset.__table__, PriceCandle.__table__, IndicatorResult.__table__]


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

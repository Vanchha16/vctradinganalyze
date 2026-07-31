from datetime import UTC, datetime

from app.models.enums import Timeframe
from app.services.market_data.providers.base import ProviderCapabilities, RawCandle
from app.services.market_data.providers.rate_limited import RateLimitedProvider


class _CountingProvider:
    name = "counting"

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
        return ProviderCapabilities(supported_timeframes=frozenset(Timeframe))


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_rate_limited_provider_allows_calls_up_to_capacity_without_sleeping() -> None:
    inner = _CountingProvider()
    clock = _FakeClock()
    sleeps: list[float] = []
    wrapped = RateLimitedProvider(inner, requests_per_minute=3, clock=clock, sleep=sleeps.append)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    for _ in range(3):
        wrapped.get_candles("EURUSD", Timeframe.M1, start, start)

    assert inner.calls == 3
    assert sleeps == []  # bucket started full - no throttling needed yet


def test_rate_limited_provider_sleeps_once_bucket_is_exhausted() -> None:
    inner = _CountingProvider()
    clock = _FakeClock()
    sleeps: list[float] = []

    def _sleep_and_advance(seconds: float) -> None:
        sleeps.append(seconds)
        clock.advance(seconds)  # simulate time passing while "asleep"

    wrapped = RateLimitedProvider(
        inner, requests_per_minute=2, clock=clock, sleep=_sleep_and_advance
    )

    start = datetime(2026, 1, 1, tzinfo=UTC)
    wrapped.get_candles("EURUSD", Timeframe.M1, start, start)  # consumes 1st token, no sleep
    wrapped.get_candles("EURUSD", Timeframe.M1, start, start)  # consumes 2nd token, no sleep
    wrapped.get_candles("EURUSD", Timeframe.M1, start, start)  # bucket empty - must sleep

    assert inner.calls == 3
    assert len(sleeps) == 1
    assert sleeps[0] > 0


def test_rate_limited_provider_delegates_name_health_and_capabilities() -> None:
    inner = _CountingProvider()
    wrapped = RateLimitedProvider(inner, requests_per_minute=60)

    assert wrapped.name == "counting"
    assert wrapped.health_check() is True
    assert Timeframe.M1 in wrapped.capabilities().supported_timeframes

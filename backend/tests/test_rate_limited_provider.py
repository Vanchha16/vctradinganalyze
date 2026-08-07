from datetime import UTC, datetime

import pytest

from app.models.enums import MarketType, Timeframe
from app.services.market_data.exceptions import DailyQuotaExceededError
from app.services.market_data.providers import rate_limited
from app.services.market_data.providers.base import ProviderCapabilities, RawCandle
from app.services.market_data.providers.rate_limited import RateLimitedProvider

_CAPABILITIES = ProviderCapabilities(
    supported_timeframes=frozenset(Timeframe),
    supported_market_types=frozenset(MarketType),
)


class _CountingProvider:
    name = "counting"

    def __init__(self) -> None:
        self.calls = 0

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        self.calls += 1
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
        return _CAPABILITIES


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class _FakeRedis:
    """In-memory stand-in for the daily-quota counter (2026-08-07) - no
    real Redis dependency, and no shared state leaking across tests the
    way a real `_redis_client` singleton keyed by "today's real UTC date"
    would."""

    def __init__(self) -> None:
        self._store: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    def expire(self, key: str, seconds: int) -> None:
        pass  # TTL cleanup isn't exercised by these tests


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limited, "_redis_client", fake)
    return fake


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


def test_daily_quota_raises_once_exhausted() -> None:
    inner = _CountingProvider()
    fake_now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    wrapped = RateLimitedProvider(
        inner, requests_per_minute=1000, requests_per_day=2, now=lambda: fake_now
    )

    start = datetime(2026, 1, 1, tzinfo=UTC)
    wrapped.get_candles("EURUSD", Timeframe.M1, start, start)
    wrapped.get_candles("EURUSD", Timeframe.M1, start, start)

    with pytest.raises(DailyQuotaExceededError) as exc_info:
        wrapped.get_candles("EURUSD", Timeframe.M1, start, start)

    assert inner.calls == 2  # the exhausting call never reached the inner provider
    error = exc_info.value
    assert error.provider == "counting"
    assert error.used == 2
    assert error.limit == 2
    assert error.reset_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_daily_quota_resets_on_new_utc_day() -> None:
    inner = _CountingProvider()
    current_day = [datetime(2026, 1, 1, 23, 59, tzinfo=UTC)]
    wrapped = RateLimitedProvider(
        inner, requests_per_minute=1000, requests_per_day=1, now=lambda: current_day[0]
    )

    start = datetime(2026, 1, 1, tzinfo=UTC)
    wrapped.get_candles("EURUSD", Timeframe.M1, start, start)
    with pytest.raises(DailyQuotaExceededError):
        wrapped.get_candles("EURUSD", Timeframe.M1, start, start)

    current_day[0] = datetime(2026, 1, 2, 0, 1, tzinfo=UTC)  # next UTC day
    wrapped.get_candles("EURUSD", Timeframe.M1, start, start)  # quota renewed

    assert inner.calls == 2


def test_no_daily_quota_configured_never_raises() -> None:
    inner = _CountingProvider()
    wrapped = RateLimitedProvider(inner, requests_per_minute=1000)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    for _ in range(10):
        wrapped.get_candles("EURUSD", Timeframe.M1, start, start)

    assert inner.calls == 10


def test_rate_limited_provider_preserves_behavior_except_quota_enforcement() -> None:
    """The decorator should be behavior-preserving: when quota allows, its
    output must be identical to calling the underlying provider directly -
    the only difference quota enforcement introduces is throttling
    (sleeping) or raising once a budget is actually exhausted."""
    inner = _CountingProvider()
    start = datetime(2026, 1, 1, tzinfo=UTC)

    direct_result = inner.get_candles("EURUSD", Timeframe.M1, start, start)
    direct_name = inner.name
    direct_health = inner.health_check()
    direct_capabilities = inner.capabilities()

    generously_wrapped = RateLimitedProvider(
        _CountingProvider(), requests_per_minute=1000, requests_per_day=1000
    )
    wrapped_result = generously_wrapped.get_candles("EURUSD", Timeframe.M1, start, start)

    assert wrapped_result == direct_result
    assert generously_wrapped.name == direct_name
    assert generously_wrapped.health_check() == direct_health
    assert generously_wrapped.capabilities() == direct_capabilities

    # Now exhaust the daily quota - behavior diverges *only* by raising,
    # not by altering what the underlying provider would have returned.
    # A distinct provider name avoids sharing `generously_wrapped`'s quota
    # bucket above - the daily counter is now keyed by provider name
    # (2026-08-07), deliberately shared across separate instances of the
    # *same* provider, but two different providers must stay independent.
    class _TightlyCountingProvider(_CountingProvider):
        name = "counting-tight"

    tightly_wrapped = RateLimitedProvider(
        _TightlyCountingProvider(), requests_per_minute=1000, requests_per_day=1
    )
    tightly_wrapped.get_candles("EURUSD", Timeframe.M1, start, start)  # consumes the only slot
    with pytest.raises(DailyQuotaExceededError):
        tightly_wrapped.get_candles("EURUSD", Timeframe.M1, start, start)


# --- Cleanup (2026-08-07): quota survives across separate instances -------


def test_daily_quota_persists_across_separate_provider_instances() -> None:
    """The actual bug this fixes: `get_market_data_providers()` builds a
    brand-new `RateLimitedProvider` on every Celery task run - the daily
    counter must survive that, or it can never reach its own cap."""
    fake_now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    first_instance = RateLimitedProvider(
        _CountingProvider(), requests_per_minute=1000, requests_per_day=2, now=lambda: fake_now
    )
    first_instance.get_candles("EURUSD", Timeframe.M1, fake_now, fake_now)
    first_instance.get_candles("EURUSD", Timeframe.M1, fake_now, fake_now)

    # A fresh instance (same provider name, same day) must inherit the
    # already-exhausted quota, not start over at zero.
    second_instance = RateLimitedProvider(
        _CountingProvider(), requests_per_minute=1000, requests_per_day=2, now=lambda: fake_now
    )
    with pytest.raises(DailyQuotaExceededError):
        second_instance.get_candles("EURUSD", Timeframe.M1, fake_now, fake_now)


def test_daily_quota_is_scoped_per_provider_name() -> None:
    """Two different providers must not share one counter."""
    fake_now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    class _OtherProvider(_CountingProvider):
        name = "other"

    exhausted = RateLimitedProvider(
        _CountingProvider(), requests_per_minute=1000, requests_per_day=1, now=lambda: fake_now
    )
    exhausted.get_candles("EURUSD", Timeframe.M1, fake_now, fake_now)
    with pytest.raises(DailyQuotaExceededError):
        exhausted.get_candles("EURUSD", Timeframe.M1, fake_now, fake_now)

    other = RateLimitedProvider(
        _OtherProvider(), requests_per_minute=1000, requests_per_day=1, now=lambda: fake_now
    )
    other.get_candles("EURUSD", Timeframe.M1, fake_now, fake_now)  # own, unexhausted quota

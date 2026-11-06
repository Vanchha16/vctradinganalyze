"""ADR-188: super admins are told when prices stop arriving, and when they
resume.

What must hold: a long silence while the market is open alerts once per
episode; the weekend, the stretch just after the Sunday reopen and gold's
daily break never alert; the return is reported; a failed send is retried;
an unreadable marker never turns into an alert on every run; and the alert
reaches super admins only.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe, UserRole
from app.models.price_candle import PriceCandle
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.services import market_data_watch
from app.services.market_data_watch import FreshnessAlert
from app.services.telegram.providers.mock import MockTelegramProvider
from app.workers import market_data_tasks

_WEDNESDAY = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
_SUNDAY_REOPEN = datetime(2026, 11, 8, 22, 0, tzinfo=UTC)


# --- The decision -----------------------------------------------------------


def test_a_long_silence_while_open_is_reported() -> None:
    newest = _WEDNESDAY - timedelta(minutes=91)

    assert market_data_watch.decide(newest, _WEDNESDAY, alerted=False) is FreshnessAlert.STALE


def test_gold_s_daily_break_is_not_an_outage() -> None:
    newest = _WEDNESDAY - timedelta(minutes=66)

    assert market_data_watch.decide(newest, _WEDNESDAY, alerted=False) is None


def test_an_episode_is_reported_once() -> None:
    newest = _WEDNESDAY - timedelta(hours=5)

    assert market_data_watch.decide(newest, _WEDNESDAY, alerted=True) is None


def test_prices_arriving_again_are_reported() -> None:
    newest = _WEDNESDAY - timedelta(minutes=2)

    assert market_data_watch.decide(newest, _WEDNESDAY, alerted=True) is FreshnessAlert.RESUMED


def test_fresh_prices_with_no_episode_say_nothing() -> None:
    newest = _WEDNESDAY - timedelta(minutes=2)

    assert market_data_watch.decide(newest, _WEDNESDAY, alerted=False) is None


def test_the_weekend_never_alerts() -> None:
    saturday = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
    friday_close = datetime(2026, 11, 6, 21, 59, tzinfo=UTC)

    assert market_data_watch.decide(friday_close, saturday, alerted=False) is None


def test_the_first_stretch_after_the_sunday_reopen_never_alerts() -> None:
    """In winter gold reopens at 23:00, an hour after the 22:00 the session
    rules use; the market must have been open for the whole threshold."""
    friday_close = datetime(2026, 11, 6, 21, 59, tzinfo=UTC)
    now = _SUNDAY_REOPEN + timedelta(minutes=89)

    assert market_data_watch.decide(friday_close, now, alerted=False) is None


def test_a_series_with_no_candles_counts_as_stopped() -> None:
    assert market_data_watch.decide(None, _WEDNESDAY, alerted=False) is FreshnessAlert.STALE


def test_a_naive_timestamp_is_read_as_utc() -> None:
    newest = (_WEDNESDAY - timedelta(minutes=91)).replace(tzinfo=None)

    assert market_data_watch.decide(newest, _WEDNESDAY, alerted=False) is FreshnessAlert.STALE


# --- The marker ---------------------------------------------------------------


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def exists(self, key: str) -> int:
        return int(key in self.store)

    def set(self, key: str, value: str) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


class _RaisingRedis:
    def exists(self, key: str) -> int:
        raise ConnectionError("simulated redis outage")

    def set(self, key: str, value: str) -> None:
        raise ConnectionError("simulated redis outage")

    def delete(self, key: str) -> None:
        raise ConnectionError("simulated redis outage")


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(market_data_watch, "_redis_client", fake)
    return fake


def test_the_marker_is_set_on_stale_and_cleared_on_resume(fake_redis: _FakeRedis) -> None:
    asset_id = uuid.uuid4()

    market_data_watch.record(asset_id, FreshnessAlert.STALE, _WEDNESDAY)
    assert market_data_watch.is_alerted(asset_id) is True

    market_data_watch.record(asset_id, FreshnessAlert.RESUMED, _WEDNESDAY)
    assert market_data_watch.is_alerted(asset_id) is False


def test_an_unreachable_redis_reads_as_unknown_and_writes_quietly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(market_data_watch, "_redis_client", _RaisingRedis())

    assert market_data_watch.is_alerted(uuid.uuid4()) is None
    market_data_watch.record(uuid.uuid4(), FreshnessAlert.STALE, _WEDNESDAY)


# --- Delivery ---------------------------------------------------------------

_TABLES = [User.__table__, TelegramAccount.__table__, Asset.__table__, PriceCandle.__table__]


@pytest.fixture
def session_factory(
    monkeypatch: pytest.MonkeyPatch, fake_redis: _FakeRedis
) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    monkeypatch.setattr(market_data_tasks, "SessionLocal", factory)
    monkeypatch.setattr(market_data_tasks.credential_resolver, "resolve", lambda name: "set")
    monkeypatch.setattr(market_data_watch, "_market_open", lambda moment: True)
    yield factory


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> MockTelegramProvider:
    instance = MockTelegramProvider()
    monkeypatch.setattr(market_data_tasks, "get_telegram_provider", lambda: instance)
    return instance


def _linked_user(session: Session, username: str, role: UserRole) -> None:
    user = User(
        email=f"{username}@example.com",
        username=username,
        password_hash="x",
        role=role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    session.add(
        TelegramAccount(
            user_id=user.id,
            telegram_chat_id=f"chat-{username}",
            link_code=uuid.uuid4().hex,
            link_code_expires_at=datetime.now(UTC),
            linked_at=datetime.now(UTC),
        )
    )


def _seed(factory: sessionmaker[Session], newest: datetime) -> uuid.UUID:
    with factory() as session:
        _linked_user(session, "operator", UserRole.SUPER_ADMIN)
        _linked_user(session, "subscriber", UserRole.REGISTERED)
        asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL)
        session.add(asset)
        session.flush()
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=Timeframe.M1,
                timestamp=newest,
                open=Decimal("4046"),
                high=Decimal("4047"),
                low=Decimal("4045"),
                close=Decimal("4046"),
                volume=Decimal("0"),
            )
        )
        session.commit()
        return asset.id


def test_a_stale_alert_reaches_super_admins_only_and_is_recorded(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    asset_id = _seed(session_factory, datetime.now(UTC) - timedelta(hours=3))

    market_data_tasks.watch_freshness_task()

    assert [chat for chat, _, _ in provider.sent_messages] == ["chat-operator"]
    assert "PRICES STOPPED" in provider.sent_messages[0][1]
    assert market_data_watch.is_alerted(asset_id) is True

    market_data_tasks.watch_freshness_task()
    assert len(provider.sent_messages) == 1


def test_the_return_is_reported_and_clears_the_marker(
    session_factory: sessionmaker[Session],
    provider: MockTelegramProvider,
    fake_redis: _FakeRedis,
) -> None:
    asset_id = _seed(session_factory, datetime.now(UTC) - timedelta(minutes=1))
    market_data_watch.record(asset_id, FreshnessAlert.STALE, datetime.now(UTC))

    market_data_tasks.watch_freshness_task()

    assert "PRICES BACK" in provider.sent_messages[0][1]
    assert market_data_watch.is_alerted(asset_id) is False


def test_a_failed_send_is_not_recorded_so_it_is_retried(
    session_factory: sessionmaker[Session],
    provider: MockTelegramProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed(session_factory, datetime.now(UTC) - timedelta(hours=3))

    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("telegram down")

    monkeypatch.setattr(provider, "send_message", broken)

    market_data_tasks.watch_freshness_task()

    assert market_data_watch.is_alerted(asset_id) is False


def test_an_unreadable_marker_skips_the_asset(
    session_factory: sessionmaker[Session],
    provider: MockTelegramProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(session_factory, datetime.now(UTC) - timedelta(hours=3))
    monkeypatch.setattr(market_data_watch, "_redis_client", _RaisingRedis())

    market_data_tasks.watch_freshness_task()

    assert provider.sent_messages == []


def test_nothing_runs_while_telegram_is_not_configured(
    session_factory: sessionmaker[Session],
    provider: MockTelegramProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(session_factory, datetime.now(UTC) - timedelta(hours=3))
    monkeypatch.setattr(market_data_tasks.credential_resolver, "resolve", lambda name: "")

    market_data_tasks.watch_freshness_task()

    assert provider.sent_messages == []


def test_the_watch_is_scheduled() -> None:
    from app.workers.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["market-data-watch-freshness"]
    assert entry["task"] == "market_data.watch_freshness"
    assert entry["schedule"] == 300.0

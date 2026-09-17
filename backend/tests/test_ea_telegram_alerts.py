"""ADR-170: Telegram alerts about the operator's EA terminals and account.

What must hold: an offline terminal is reported once per outage and only while
the market is open, its return is reported, a reached daily loss limit is
reported once per blocked day, an alert whose send failed is retried, and
every EA alert reaches super admins only - never other Telegram subscribers.
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
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import UserRole
from app.models.signal import Signal
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.services import ea_terminal_watch
from app.services.ea_terminal_watch import TerminalAlert
from app.services.telegram.providers.mock import MockTelegramProvider
from app.workers import ea_tasks, telegram_tasks

_NOW = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)  # a Wednesday, market open

_TABLES = [
    User.__table__,
    TelegramAccount.__table__,
    EaToken.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    EaExecutionEvent.__table__,
]


def _token(**fields: object) -> EaToken:
    """A token for the pure-decision tests, which pass `_NOW` into
    `decide()` explicitly.

    **`last_used_at` defaults to `_NOW - 30s`, a fixed instant.** That is
    correct only when the test also supplies `_NOW` as "now". Any test that
    drives `ea_tasks.watch_terminals_task()` is measured against the real
    clock instead, and must seed `last_used_at` relative to
    `datetime.now(UTC)` - otherwise the terminal reads as offline the day
    after this constant, and an OFFLINE alert displaces whatever the test
    was actually about.
    """
    values: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "name": "WinserverEA",
        "token_hash": uuid.uuid4().hex,
        "hint": "Jk0I",
        "last_used_at": _NOW - timedelta(seconds=30),
        "effective_dry_run": False,
        "effective_paused": False,
    }
    values.update(fields)
    return EaToken(**values)


# --- The decision -----------------------------------------------------------


def test_a_terminal_silent_past_the_threshold_is_reported_offline() -> None:
    token = _token(last_used_at=_NOW - timedelta(minutes=6))

    decision = ea_terminal_watch.decide(token, _NOW, is_market_open=True)

    assert decision.alerts == (TerminalAlert.OFFLINE,)
    assert decision.offline_alerted_at == _NOW


def test_a_short_silence_is_not_an_outage() -> None:
    token = _token(last_used_at=_NOW - timedelta(minutes=4))

    decision = ea_terminal_watch.decide(token, _NOW, is_market_open=True)

    assert decision.alerts == ()
    assert not decision.changes(token)


def test_an_offline_terminal_is_not_reported_while_the_market_is_closed() -> None:
    """Nothing to miss over the weekend - it is reported when the market reopens."""
    token = _token(last_used_at=_NOW - timedelta(hours=30))

    assert ea_terminal_watch.decide(token, _NOW, is_market_open=False).alerts == ()


def test_an_outage_is_reported_once() -> None:
    token = _token(
        last_used_at=_NOW - timedelta(minutes=40), offline_alerted_at=_NOW - timedelta(minutes=35)
    )

    decision = ea_terminal_watch.decide(token, _NOW, is_market_open=True)

    assert decision.alerts == ()
    assert not decision.changes(token)


def test_polling_again_after_an_offline_alert_is_reported_back_online() -> None:
    token = _token(offline_alerted_at=_NOW - timedelta(minutes=20))

    decision = ea_terminal_watch.decide(token, _NOW, is_market_open=True)

    assert decision.alerts == (TerminalAlert.BACK_ONLINE,)
    assert decision.offline_alerted_at is None


def test_back_online_is_reported_even_after_the_market_closed() -> None:
    token = _token(offline_alerted_at=_NOW - timedelta(minutes=20))

    decision = ea_terminal_watch.decide(token, _NOW, is_market_open=False)

    assert decision.alerts == (TerminalAlert.BACK_ONLINE,)


def test_a_reached_loss_limit_is_reported_once_per_blocked_day() -> None:
    blocked = _token(effective_loss_blocked=True)

    first = ea_terminal_watch.decide(blocked, _NOW, is_market_open=True)
    blocked.loss_limit_alerted_at = first.loss_limit_alerted_at
    again = ea_terminal_watch.decide(blocked, _NOW, is_market_open=True)

    assert first.alerts == (TerminalAlert.LOSS_LIMIT,)
    assert again.alerts == ()


def test_the_loss_alert_re_arms_silently_when_a_new_day_lifts_the_block() -> None:
    token = _token(effective_loss_blocked=False, loss_limit_alerted_at=_NOW - timedelta(hours=9))

    decision = ea_terminal_watch.decide(token, _NOW, is_market_open=True)

    assert decision.alerts == ()
    assert decision.loss_limit_alerted_at is None
    assert decision.changes(token)


def test_an_ea_that_never_reports_the_limit_never_alerts_about_it() -> None:
    """Before EA 1.30 `effective_loss_blocked` is null."""
    assert ea_terminal_watch.decide(_token(), _NOW, is_market_open=True).alerts == ()


def test_a_token_never_polled_has_nothing_to_report() -> None:
    token = _token(last_used_at=None)

    assert ea_terminal_watch.decide(token, _NOW, is_market_open=True).alerts == ()


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 9, 16, 10, 0, tzinfo=UTC), True),  # Wednesday
        (datetime(2026, 9, 19, 10, 0, tzinfo=UTC), False),  # Saturday
        (datetime(2026, 9, 18, 22, 30, tzinfo=UTC), False),  # Friday after the close
        (datetime(2026, 9, 20, 22, 30, tzinfo=UTC), True),  # Sunday after the open
    ],
)
def test_market_hours(moment: datetime, expected: bool) -> None:
    assert ea_terminal_watch.market_open(moment) is expected


# --- Delivery ---------------------------------------------------------------


@pytest.fixture
def session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    monkeypatch.setattr(ea_tasks, "SessionLocal", factory)
    monkeypatch.setattr(telegram_tasks, "SessionLocal", factory)
    monkeypatch.setattr(ea_tasks.credential_resolver, "resolve", lambda name: "configured")
    monkeypatch.setattr(ea_tasks.ea_terminal_watch, "market_open", lambda now: True)
    yield factory


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> MockTelegramProvider:
    instance = MockTelegramProvider()
    monkeypatch.setattr(ea_tasks, "get_telegram_provider", lambda: instance)
    monkeypatch.setattr(telegram_tasks, "get_telegram_provider", lambda: instance)
    return instance


def _linked_user(session: Session, username: str, role: UserRole) -> User:
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
    session.commit()
    return user


def _seed(factory: sessionmaker[Session], **token_fields: object) -> uuid.UUID:
    with factory() as session:
        operator = _linked_user(session, "operator", UserRole.SUPER_ADMIN)
        _linked_user(session, "subscriber", UserRole.REGISTERED)
        token = _token(user_id=operator.id, **token_fields)
        session.add(token)
        session.commit()
        return token.id


def _chats(provider: MockTelegramProvider) -> list[str]:
    return [chat_id for chat_id, _, _ in provider.sent_messages]


def test_an_offline_alert_reaches_super_admins_only_and_is_recorded(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    token_id = _seed(session_factory, last_used_at=datetime.now(UTC) - timedelta(minutes=12))

    ea_tasks.watch_terminals_task()
    ea_tasks.watch_terminals_task()

    assert _chats(provider) == ["chat-operator"]
    assert "EA OFFLINE" in provider.sent_messages[0][1]
    with session_factory() as session:
        stored = session.get(EaToken, token_id)
        assert stored is not None
        assert stored.offline_alerted_at is not None


def test_a_failed_send_is_retried_on_the_next_run(
    session_factory: sessionmaker[Session],
    provider: MockTelegramProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `last_used_at` is seeded relative to the REAL clock, not `_NOW`.
    # `watch_terminals_task` calls `datetime.now(UTC)` itself, so a token
    # anchored to `_NOW` reads as long-silent once real time moves past it -
    # the terminal is then reported OFFLINE and that alert, not the loss
    # limit, is `sent_messages[0]`. This test passed only on 2026-09-16.
    token_id = _seed(
        session_factory,
        effective_loss_blocked=True,
        ea_currency="USC",
        last_used_at=datetime.now(UTC) - timedelta(seconds=30),
    )

    def broken(chat_id: str, text: str, **_: object) -> None:
        raise RuntimeError("telegram is down")

    monkeypatch.setattr(provider, "send_message", broken)
    ea_tasks.watch_terminals_task()
    with session_factory() as session:
        stored = session.get(EaToken, token_id)
        assert stored is not None
        assert stored.loss_limit_alerted_at is None

    monkeypatch.undo()
    monkeypatch.setattr(ea_tasks, "SessionLocal", session_factory)
    monkeypatch.setattr(ea_tasks, "get_telegram_provider", lambda: provider)
    monkeypatch.setattr(ea_tasks.credential_resolver, "resolve", lambda name: "configured")
    ea_tasks.watch_terminals_task()

    assert "DAILY LOSS LIMIT REACHED" in provider.sent_messages[0][1]


def test_nothing_is_sent_or_recorded_while_telegram_is_not_configured(
    session_factory: sessionmaker[Session],
    provider: MockTelegramProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token_id = _seed(session_factory, last_used_at=datetime.now(UTC) - timedelta(hours=2))
    monkeypatch.setattr(ea_tasks.credential_resolver, "resolve", lambda name: None)

    ea_tasks.watch_terminals_task()

    assert provider.sent_messages == []
    with session_factory() as session:
        stored = session.get(EaToken, token_id)
        assert stored is not None
        assert stored.offline_alerted_at is None


def test_an_ea_event_message_reaches_super_admins_only(
    session_factory: sessionmaker[Session], provider: MockTelegramProvider
) -> None:
    with session_factory() as session:
        operator = _linked_user(session, "operator", UserRole.SUPER_ADMIN)
        _linked_user(session, "subscriber", UserRole.REGISTERED)
        event = EaExecutionEvent(
            user_id=operator.id,
            token_name="WinserverEA",
            signal_id=uuid.uuid4(),
            event_key="160018306:live:closed:880112",
            event_type="position_closed",
            dry_run=False,
            occurred_at=datetime.now(UTC),
            account_login="160018306",
            broker_symbol="XAUUSDc",
            volume=Decimal("0.40"),
            price=Decimal("4345.790"),
            profit=Decimal("-245.20"),
            currency="USC",
            close_reason="sl",
        )
        session.add(event)
        session.commit()
        event_id = str(event.id)

    telegram_tasks.send_ea_event_telegram_task(event_id)

    assert _chats(provider) == ["chat-operator"]
    assert "TRADE CLOSED" in provider.sent_messages[0][1]

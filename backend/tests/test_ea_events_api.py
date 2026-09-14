"""EA execution event reports and the activity listing (ADR-162).

What must hold: a re-sent batch never double-stores, one bad event never
sinks the good ones in its batch, only the owner can read events back, an
EA token can report but not read, history survives token revocation, and
only a live fill or close moves a signal (ADR-172).
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.routes import ea as ea_routes
from app.database.base import Base
from app.dependencies import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import MarketType, SignalStatus, SignalType, Timeframe, UserRole
from app.models.signal import Signal
from app.models.user import User
from app.utils.time import as_aware_utc

_TABLES = [
    User.__table__,
    EaToken.__table__,
    AuditLog.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    EaExecutionEvent.__table__,
]


@pytest.fixture
def session_engine() -> Generator[object, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    yield engine


@pytest.fixture(autouse=True)
def queued(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """ADR-170 - event ids queued for Telegram, instead of reaching Celery."""
    sent: list[str] = []
    monkeypatch.setattr(ea_routes, "enqueue_ea_event_delivery", sent.append)
    return sent


@pytest.fixture(autouse=True)
def signal_news(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """ADR-172 - the website update (the status it announced) and subscriber
    messages for signals a live fill or close moved."""
    news: dict[str, list[str]] = {"changed": [], "triggered": [], "outcome": []}
    monkeypatch.setattr(
        ea_routes,
        "publish_signal_status_changed",
        lambda signal: news["changed"].append(signal.status.value),
    )
    monkeypatch.setattr(ea_routes, "enqueue_signal_triggered_delivery", news["triggered"].append)
    monkeypatch.setattr(ea_routes, "enqueue_signal_outcome_delivery", news["outcome"].append)
    return news


@pytest.fixture
def db(session_engine: object) -> Generator[Session, None, None]:
    with Session(session_engine) as session:  # type: ignore[arg-type]
        yield session


@pytest.fixture
def client(session_engine: object) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        s = Session(session_engine)  # type: ignore[arg-type]
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _user(db: Session, username: str = "root", role: UserRole = UserRole.SUPER_ADMIN) -> User:
    user = User(
        email=f"{username}@example.com",
        username=username,
        password_hash="x",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _logout() -> None:
    app.dependency_overrides.pop(get_current_user, None)


def _signal(db: Session, signal_type: SignalType = SignalType.BUY) -> Signal:
    asset = db.query(Asset).filter_by(symbol="XAUUSD").one_or_none()
    if asset is None:
        asset = Asset(symbol="XAUUSD", name="Gold / US Dollar", market_type=MarketType.METAL)
        db.add(asset)
        db.commit()
    signal = Signal(
        analysis_id=uuid.uuid4(),
        asset_id=asset.id,
        timeframe=Timeframe.H1,
        signal_type=signal_type,
        entry_price=Decimal("4414.236"),
        stop_loss=Decimal("4400.000"),
        take_profit=Decimal("4440.000"),
        risk_reward=1.8,
        confidence=72.0,
        status=SignalStatus.ACTIVE,
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def _token(client: TestClient, user: User, name: str = "Home PC") -> dict[str, Any]:
    _as(user)
    response = client.post("/api/v1/ea/tokens", json={"name": name})
    assert response.status_code == 201, response.text
    _logout()
    body: dict[str, Any] = response.json()
    return body


def _event(
    signal: Signal, key: str, event_type: str = "dry_run_checked", **extra: Any
) -> dict[str, Any]:
    return {
        "event_key": key,
        "event_type": event_type,
        "signal_id": str(signal.id),
        "dry_run": True,
        "occurred_at": int(datetime.now(UTC).timestamp()),
        "account_login": "160018306",
        "broker_symbol": "XAUUSDc",
        "order_type": "buy_limit",
        "volume": 0.01,
        "price": 4414.236,
        "stop_loss": 4400.0,
        "take_profit": 4440.0,
        "retcode": 0,
        "message": "would be accepted",
        **extra,
    }


def _report(
    client: TestClient, raw_token: str | None, events: list[dict[str, Any]]
) -> httpx.Response:
    headers = {"X-EA-Token": raw_token} if raw_token is not None else {}
    return client.post("/api/v1/ea/events", json={"events": events}, headers=headers)


# --- Reporting --------------------------------------------------------------


def test_a_batch_is_stored_with_the_reporting_terminal(client: TestClient, db: Session) -> None:
    user = _user(db)
    token = _token(client, user)
    signal = _signal(db)

    response = _report(
        client,
        token["token"],
        [_event(signal, "dry:a"), _event(signal, "placed:a", "order_placed", order_ticket=9001)],
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"accepted": 2, "duplicates": 0, "rejected": []}
    rows = db.query(EaExecutionEvent).order_by(EaExecutionEvent.event_key).all()
    assert [r.event_key for r in rows] == ["dry:a", "placed:a"]
    assert {r.token_name for r in rows} == {"Home PC"}
    assert {r.user_id for r in rows} == {user.id}
    assert rows[1].order_ticket == 9001
    assert rows[0].price == Decimal("4414.236")


def test_resending_a_batch_does_not_store_it_twice(client: TestClient, db: Session) -> None:
    """The EA re-sends whenever it did not get a response - a lost
    response must not turn one fill into two."""
    token = _token(client, _user(db))
    signal = _signal(db)
    batch = [_event(signal, "opened:777", "position_opened")]

    _report(client, token["token"], batch)
    again = _report(client, token["token"], batch)

    assert again.json() == {"accepted": 0, "duplicates": 1, "rejected": []}
    assert db.query(EaExecutionEvent).count() == 1


def test_a_key_repeated_inside_one_batch_is_stored_once(client: TestClient, db: Session) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)

    response = _report(client, token["token"], [_event(signal, "k"), _event(signal, "k")])

    assert response.json() == {"accepted": 1, "duplicates": 1, "rejected": []}


def test_one_unknown_signal_does_not_sink_the_batch(client: TestClient, db: Session) -> None:
    """The EA drops a batch once it gets any response, so failing the
    whole batch for one event would lose the good ones with it."""
    token = _token(client, _user(db))
    signal = _signal(db)
    ghost = _event(signal, "ghost")
    ghost["signal_id"] = str(uuid.uuid4())

    response = _report(client, token["token"], [_event(signal, "good"), ghost])

    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    assert response.json()["rejected"] == [{"event_key": "ghost", "reason": "unknown signal_id"}]


def test_an_overlong_message_is_truncated_not_rejected(client: TestClient, db: Session) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)

    response = _report(client, token["token"], [_event(signal, "long", message="x" * 400)])

    assert response.json()["accepted"] == 1
    assert len(db.query(EaExecutionEvent).one().message or "") == 255


@pytest.mark.parametrize("size", [0, 51])
def test_batch_size_is_bounded(client: TestClient, db: Session, size: int) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)

    response = _report(client, token["token"], [_event(signal, f"k{i}") for i in range(size)])

    assert response.status_code == 422


def test_an_unknown_event_type_is_rejected(client: TestClient, db: Session) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)

    response = _report(client, token["token"], [_event(signal, "k", "margin_called")])

    assert response.status_code == 422


def test_reporting_requires_an_ea_token(client: TestClient, db: Session) -> None:
    signal = _signal(db)

    assert _report(client, None, [_event(signal, "k")]).status_code == 401
    assert _report(client, "vcea_forged", [_event(signal, "k")]).status_code == 401


def test_a_session_cannot_report_events(client: TestClient, db: Session) -> None:
    """Only a terminal reports what a terminal did."""
    _as(_user(db))
    signal = _signal(db)

    assert _report(client, None, [_event(signal, "k")]).status_code == 401


# --- Moving the signal (ADR-172) --------------------------------------------


def _stored(db: Session, signal: Signal) -> Signal:
    db.expire_all()
    stored = db.get(Signal, signal.id)
    assert stored is not None
    return stored


def test_a_live_fill_and_take_profit_move_the_signal(
    client: TestClient, db: Session, signal_news: dict[str, list[str]]
) -> None:
    """The broker's fill is what really happened - on 2026-09-14 Twelve Data
    missed the entry by 0.36 and the website never saw the fill."""
    token = _token(client, _user(db))
    signal = _signal(db)
    now = int(datetime.now(UTC).timestamp())

    _report(
        client,
        token["token"],
        [
            # Close listed first on purpose: the fill is still applied first.
            _event(
                signal,
                "closed:1",
                "position_closed",
                dry_run=False,
                occurred_at=now,
                price=4440.0,
                profit=25.76,
                close_reason="tp",
            ),
            _event(signal, "opened:1", "position_opened", dry_run=False, occurred_at=now - 600),
        ],
    )

    stored = _stored(db, signal)
    assert stored.status == SignalStatus.SUCCESSFUL
    assert as_aware_utc(stored.triggered_at) == datetime.fromtimestamp(now - 600, UTC)  # type: ignore[arg-type]
    assert as_aware_utc(stored.closed_at) == datetime.fromtimestamp(now, UTC)  # type: ignore[arg-type]
    assert stored.profit_loss == Decimal("25.764")
    assert signal_news == {
        "changed": ["successful"],
        "triggered": [str(signal.id)],
        "outcome": [str(signal.id)],
    }


def test_a_dry_run_report_never_changes_the_signal(
    client: TestClient, db: Session, signal_news: dict[str, list[str]]
) -> None:
    """ADR-162 still holds for everything but a live fill or close."""
    token = _token(client, _user(db))
    signal = _signal(db)

    _report(
        client,
        token["token"],
        [
            _event(signal, "opened:1", "position_opened"),
            _event(signal, "closed:2", "position_closed", profit=25.76, close_reason="tp"),
        ],
    )

    stored = _stored(db, signal)
    assert stored.status == SignalStatus.ACTIVE
    assert stored.closed_at is None
    assert stored.profit_loss is None
    assert signal_news == {"changed": [], "triggered": [], "outcome": []}


def test_a_hand_close_ends_the_trade_without_a_subscriber_message(
    client: TestClient, db: Session, signal_news: dict[str, list[str]]
) -> None:
    """Left filled, a trade closed by hand would block every newer signal
    (ADR-168). The outcome message only knows take profit and stop loss."""
    token = _token(client, _user(db))
    signal = _signal(db)

    _report(client, token["token"], [_event(signal, "opened:1", "position_opened", dry_run=False)])
    _report(
        client,
        token["token"],
        [
            _event(
                signal,
                "closed:1",
                "position_closed",
                dry_run=False,
                price=4420.0,
                close_reason="manual",
            )
        ],
    )

    stored = _stored(db, signal)
    assert stored.status == SignalStatus.CLOSED
    assert stored.status_reason == "Closed by hand on the EA's account."
    assert stored.profit_loss == Decimal("5.764")
    assert signal_news == {
        "changed": ["triggered", "closed"],
        "triggered": [str(signal.id)],
        "outcome": [],
    }


def test_a_resent_fill_moves_and_announces_the_signal_once(
    client: TestClient, db: Session, signal_news: dict[str, list[str]]
) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)
    batch = [_event(signal, "opened:1", "position_opened", dry_run=False)]

    _report(client, token["token"], batch)
    _report(client, token["token"], batch)

    assert _stored(db, signal).status == SignalStatus.TRIGGERED
    assert signal_news == {"changed": ["triggered"], "triggered": [str(signal.id)], "outcome": []}


def test_a_late_fill_moves_the_signal_but_sends_no_message(
    client: TestClient, db: Session, signal_news: dict[str, list[str]]
) -> None:
    """A terminal catching up after an outage corrects the website quietly."""
    token = _token(client, _user(db))
    signal = _signal(db)
    hours_ago = int((datetime.now(UTC) - timedelta(hours=7)).timestamp())

    _report(
        client,
        token["token"],
        [_event(signal, "opened:1", "position_opened", dry_run=False, occurred_at=hours_ago)],
    )

    assert _stored(db, signal).status == SignalStatus.TRIGGERED
    assert signal_news == {"changed": ["triggered"], "triggered": [], "outcome": []}


def test_a_fill_for_a_cancelled_signal_leaves_it_cancelled(
    client: TestClient, db: Session, signal_news: dict[str, list[str]]
) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)
    signal.status = SignalStatus.CANCELLED
    db.commit()

    _report(client, token["token"], [_event(signal, "opened:1", "position_opened", dry_run=False)])

    assert _stored(db, signal).status == SignalStatus.CANCELLED
    assert signal_news == {"changed": [], "triggered": [], "outcome": []}


# --- Telegram (ADR-170) -----------------------------------------------------


def test_live_events_the_operator_acts_on_are_queued_for_telegram(
    client: TestClient, db: Session, queued: list[str]
) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)

    _report(
        client,
        token["token"],
        [
            _event(signal, "dry", "dry_run_checked"),
            _event(signal, "placed", "order_placed", dry_run=False, order_ticket=9001),
            _event(signal, "closed", "position_closed", dry_run=False, profit=-245.2),
        ],
    )

    stored = {r.event_key: str(r.id) for r in db.query(EaExecutionEvent).all()}
    assert queued == [stored["placed"], stored["closed"]]


def test_a_resent_batch_is_not_queued_again(
    client: TestClient, db: Session, queued: list[str]
) -> None:
    """The EA re-sends after a lost response - one fill must not become two
    Telegram messages."""
    token = _token(client, _user(db))
    signal = _signal(db)
    batch = [_event(signal, "opened:1", "position_opened", dry_run=False)]

    _report(client, token["token"], batch)
    _report(client, token["token"], batch)

    assert len(queued) == 1


def test_dry_run_events_are_never_queued(
    client: TestClient, db: Session, queued: list[str]
) -> None:
    token = _token(client, _user(db))
    signal = _signal(db)

    _report(client, token["token"], [_event(signal, "placed", "order_placed", dry_run=True)])

    assert queued == []


def test_a_late_arriving_event_is_stored_but_not_queued(
    client: TestClient, db: Session, queued: list[str]
) -> None:
    """A terminal catching up after an outage must not flood the chat."""
    token = _token(client, _user(db))
    signal = _signal(db)
    hours_ago = int((datetime.now(UTC) - timedelta(hours=7)).timestamp())

    response = _report(
        client,
        token["token"],
        [_event(signal, "old", "position_closed", dry_run=False, occurred_at=hours_ago)],
    )

    assert response.json()["accepted"] == 1
    assert queued == []


# --- Listing ----------------------------------------------------------------


def test_listing_is_newest_first_with_the_signal_direction(
    client: TestClient, db: Session
) -> None:
    user = _user(db)
    token = _token(client, user)
    signal = _signal(db, SignalType.SELL)
    now = int(datetime.now(UTC).timestamp())
    _report(
        client,
        token["token"],
        [
            _event(signal, "older", occurred_at=now - 120),
            _event(signal, "newer", "order_placed", occurred_at=now - 10),
        ],
    )

    _as(user)
    body = client.get("/api/v1/ea/events").json()

    assert body["total"] == 2
    assert [i["event_type"] for i in body["items"]] == ["order_placed", "dry_run_checked"]
    assert body["items"][0]["signal_type"] == "sell"
    assert body["items"][0]["price"] == pytest.approx(4414.236)


def test_listing_filters(client: TestClient, db: Session) -> None:
    user = _user(db)
    token = _token(client, user)
    first, second = _signal(db), _signal(db)
    _report(
        client,
        token["token"],
        [
            _event(first, "a", "dry_run_checked", dry_run=True),
            _event(first, "b", "order_placed", dry_run=False),
            _event(second, "c", "order_placed", dry_run=False),
        ],
    )
    _as(user)

    def keys(**params: Any) -> int:
        total: int = client.get("/api/v1/ea/events", params=params).json()["total"]
        return total

    assert keys(signal_id=str(first.id)) == 2
    assert keys(dry_run="false") == 2
    assert keys(dry_run="true") == 1
    assert keys(event_type="order_placed", signal_id=str(second.id)) == 1


def test_a_user_sees_only_their_own_events(client: TestClient, db: Session) -> None:
    owner = _user(db, "owner")
    other = _user(db, "other")
    signal = _signal(db)
    _report(client, _token(client, owner)["token"], [_event(signal, "mine")])

    _as(other)

    assert client.get("/api/v1/ea/events").json()["total"] == 0


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.REGISTERED])
def test_listing_is_super_admin_only(client: TestClient, db: Session, role: UserRole) -> None:
    _as(_user(db, "someone", role))

    assert client.get("/api/v1/ea/events").status_code == 403


def test_an_ea_token_cannot_read_events_back(client: TestClient, db: Session) -> None:
    token = _token(client, _user(db))

    response = client.get("/api/v1/ea/events", headers={"X-EA-Token": token["token"]})

    assert response.status_code == 401


def test_history_survives_revoking_the_token(client: TestClient, db: Session) -> None:
    """Revoking a terminal stops it; it must not erase what it did."""
    user = _user(db)
    token = _token(client, user, "Old VPS")
    signal = _signal(db)
    _report(client, token["token"], [_event(signal, "k")])

    _as(user)
    assert client.delete(f"/api/v1/ea/tokens/{token['id']}").status_code == 204

    [item] = client.get("/api/v1/ea/events").json()["items"]
    assert item["token_name"] == "Old VPS"

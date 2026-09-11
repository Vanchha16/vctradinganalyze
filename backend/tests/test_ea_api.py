"""MT5 Expert Advisor token management and signal feed (ADR-161).

The tests that matter most are the negative ones: an EA token reaches
nothing but the feed, a session cannot read the feed, the raw token is
never stored or returned twice, and a token stops working the moment its
owner is revoked, demoted or deactivated.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.base import Base
from app.dependencies import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.ea_token import EaToken
from app.models.enums import MarketType, SignalStatus, SignalType, Timeframe, UserRole
from app.models.signal import Signal
from app.models.user import User
from app.services.ea_service import MAX_TOKENS_PER_USER

_TABLES = [
    User.__table__,
    EaToken.__table__,
    AuditLog.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
]


@pytest.fixture
def session_engine() -> Generator[object, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    yield engine


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


def _user(db: Session, role: UserRole = UserRole.SUPER_ADMIN, username: str = "root") -> User:
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


def _asset(db: Session, symbol: str = "XAUUSD") -> Asset:
    asset = Asset(symbol=symbol, name="Gold / US Dollar", market_type=MarketType.METAL)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _signal(
    db: Session,
    asset: Asset,
    *,
    status: SignalStatus = SignalStatus.ACTIVE,
    age: timedelta = timedelta(minutes=5),
    triggered_ago: timedelta | None = None,
    signal_type: SignalType = SignalType.BUY,
) -> Signal:
    now = datetime.now(UTC)
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
        status=status,
        created_at=now - age,
        triggered_at=now - triggered_ago if triggered_ago is not None else None,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def _create_token(client: TestClient, name: str = "Home PC") -> dict[str, object]:
    response = client.post("/api/v1/ea/tokens", json={"name": name})
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _feed(client: TestClient, token: str | None, symbol: str = "XAUUSD") -> httpx.Response:
    headers = {"X-EA-Token": token} if token is not None else {}
    return client.get("/api/v1/ea/signals", params={"symbol": symbol}, headers=headers)


# --- Token management -------------------------------------------------------


def test_super_admin_creates_a_token_shown_once(client: TestClient, db: Session) -> None:
    _as(_user(db))

    body = _create_token(client)

    raw = str(body["token"])
    assert raw.startswith("vcea_")
    assert body["hint"] == raw[-4:]
    assert body["name"] == "Home PC"


def test_the_raw_token_is_never_stored(client: TestClient, db: Session) -> None:
    """A database dump - `~/deploy_backups` holds one per deploy - must not
    contain a working token."""
    _as(_user(db))
    raw = str(_create_token(client)["token"])

    row = db.query(EaToken).one()

    assert row.token_hash != raw
    assert raw not in row.token_hash
    assert len(row.token_hash) == 64


def test_listing_never_returns_the_raw_token(client: TestClient, db: Session) -> None:
    _as(_user(db))
    raw = str(_create_token(client)["token"])

    listed = client.get("/api/v1/ea/tokens")

    assert listed.status_code == 200
    assert raw not in listed.text
    assert "token" not in listed.json()["items"][0]


def test_the_raw_token_never_reaches_the_audit_log(client: TestClient, db: Session) -> None:
    _as(_user(db))
    raw = str(_create_token(client)["token"])

    entries = db.query(AuditLog).all()

    assert [e.action for e in entries] == ["ea_token_created"]
    assert raw not in str(entries[0].context)


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.REGISTERED])
def test_only_a_super_admin_can_manage_tokens(
    client: TestClient, db: Session, role: UserRole
) -> None:
    """Execution is single-operator for now (ADR-161)."""
    _as(_user(db, role, "someone"))

    assert client.post("/api/v1/ea/tokens", json={"name": "x"}).status_code == 403
    assert client.get("/api/v1/ea/tokens").status_code == 403


def test_managing_tokens_requires_a_session(client: TestClient, db: Session) -> None:
    assert client.get("/api/v1/ea/tokens").status_code == 401


def test_a_blank_name_is_rejected(client: TestClient, db: Session) -> None:
    _as(_user(db))

    assert client.post("/api/v1/ea/tokens", json={"name": "   "}).status_code == 422


def test_token_count_is_capped(client: TestClient, db: Session) -> None:
    _as(_user(db))
    for i in range(MAX_TOKENS_PER_USER):
        _create_token(client, f"terminal {i}")

    response = client.post("/api/v1/ea/tokens", json={"name": "one too many"})

    assert response.status_code == 409
    assert db.query(EaToken).count() == MAX_TOKENS_PER_USER


def test_revoking_another_users_token_is_404(client: TestClient, db: Session) -> None:
    """404, not 403 - the response must not confirm the id exists."""
    owner = _user(db, username="owner")
    _as(owner)
    token_id = _create_token(client)["id"]

    _as(_user(db, username="other"))
    response = client.delete(f"/api/v1/ea/tokens/{token_id}")

    assert response.status_code == 404
    assert db.query(EaToken).count() == 1


# --- Feed authentication ----------------------------------------------------


def test_the_feed_rejects_a_missing_token(client: TestClient, db: Session) -> None:
    _asset(db)

    assert _feed(client, None).status_code == 401

@pytest.mark.parametrize("token", ["vcea_not-a-real-token", "not-even-the-prefix", ""])
def test_the_feed_rejects_an_unknown_token(client: TestClient, db: Session, token: str) -> None:
    _asset(db)

    response = _feed(client, token)

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_ea_token"


def test_a_session_cannot_read_the_feed(client: TestClient, db: Session) -> None:
    """The feed authenticates on `X-EA-Token` only. A logged-in browser
    session must not be a way in - that would make every session token
    an EA token too."""
    _asset(db)
    _as(_user(db))

    assert _feed(client, None).status_code == 401


def test_an_ea_token_is_not_a_session(client: TestClient, db: Session) -> None:
    """The reverse: the token reaches the feed and nothing else."""
    _as(_user(db))
    raw = str(_create_token(client)["token"])
    _logout()

    response = client.get("/api/v1/signals", headers={"Authorization": f"Bearer {raw}"})

    assert response.status_code == 401


def test_a_revoked_token_stops_working(client: TestClient, db: Session) -> None:
    _asset(db)
    _as(_user(db))
    created = _create_token(client)
    raw = str(created["token"])
    assert _feed(client, raw).status_code == 200

    assert client.delete(f"/api/v1/ea/tokens/{created['id']}").status_code == 204

    assert _feed(client, raw).status_code == 401
    assert db.query(AuditLog).filter_by(action="ea_token_revoked").count() == 1


def test_a_demoted_users_token_stops_working(client: TestClient, db: Session) -> None:
    """The role is checked on every poll, not only at creation."""
    _asset(db)
    user = _user(db)
    _as(user)
    raw = str(_create_token(client)["token"])

    user.role = UserRole.ADMIN
    db.commit()

    assert _feed(client, raw).status_code == 401


def test_a_deactivated_users_token_stops_working(client: TestClient, db: Session) -> None:
    _asset(db)
    user = _user(db)
    _as(user)
    raw = str(_create_token(client)["token"])

    user.is_active = False
    db.commit()

    assert _feed(client, raw).status_code == 401


def test_the_feed_records_last_used(client: TestClient, db: Session) -> None:
    _asset(db)
    _as(_user(db))
    raw = str(_create_token(client)["token"])
    _logout()

    _feed(client, raw)

    db.expire_all()
    assert db.query(EaToken).one().last_used_at is not None


# --- Feed content -----------------------------------------------------------


def _ready(client: TestClient, db: Session) -> tuple[str, Asset]:
    asset = _asset(db)
    _as(_user(db))
    raw = str(_create_token(client)["token"])
    _logout()
    return raw, asset


def test_the_feed_returns_an_active_signal_with_epoch_times(
    client: TestClient, db: Session
) -> None:
    raw, asset = _ready(client, db)
    signal = _signal(db, asset)

    response = _feed(client, raw)

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "XAUUSD"
    assert isinstance(body["server_time"], int)
    [item] = body["signals"]
    assert item["id"] == str(signal.id)
    assert item["signal_type"] == "buy"
    assert item["status"] == "active"
    assert item["entry_price"] == pytest.approx(4414.236)
    assert item["stop_loss"] == pytest.approx(4400.0)
    assert item["take_profit"] == pytest.approx(4440.0)
    # expires_at is creation + the pending-entry TTL, as epoch seconds.
    assert item["expires_at"] - item["created_at"] == settings.signal_ttl_hours * 3600


def test_the_feed_keeps_a_triggered_signal(client: TestClient, db: Session) -> None:
    """An EA holding an order for a triggered signal needs to keep seeing
    it - dropping it would read as "cancel"."""
    raw, asset = _ready(client, db)
    _signal(
        db,
        asset,
        status=SignalStatus.TRIGGERED,
        age=timedelta(hours=2),
        triggered_ago=timedelta(hours=1),
    )

    [item] = _feed(client, raw).json()["signals"]
    assert item["status"] == "triggered"
    assert item["triggered_at"] is not None


def test_the_feed_drops_an_expired_signal(client: TestClient, db: Session) -> None:
    """Stored ACTIVE but past its TTL is EXPIRED at read time (ADR-088) -
    the stored column alone would have kept it in the feed forever."""
    raw, asset = _ready(client, db)
    _signal(db, asset, age=timedelta(hours=settings.signal_ttl_hours + 1))

    assert _feed(client, raw).json()["signals"] == []

@pytest.mark.parametrize("status", [SignalStatus.SUCCESSFUL, SignalStatus.STOPPED_OUT])
def test_the_feed_drops_a_finished_signal(
    client: TestClient, db: Session, status: SignalStatus
) -> None:
    raw, asset = _ready(client, db)
    _signal(db, asset, status=status, triggered_ago=timedelta(minutes=30))

    assert _feed(client, raw).json()["signals"] == []

def test_the_feed_is_scoped_to_the_requested_symbol(client: TestClient, db: Session) -> None:
    raw, xau = _ready(client, db)
    eur = _asset(db, "EURUSD")
    _signal(db, xau)
    _signal(db, eur)

    body = _feed(client, raw, "xauusd").json()
    assert len(body["signals"]) == 1
    assert body["signals"][0]["symbol"] == "XAUUSD"


def test_the_feed_404s_an_unknown_symbol(client: TestClient, db: Session) -> None:
    raw, _ = _ready(client, db)

    assert _feed(client, raw, "NOPE").status_code == 404
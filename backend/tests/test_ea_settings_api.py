"""Website-controlled EA settings and the terminal's self-report (ADR-163).

What must hold: an unconfigured token changes nothing, only the owner's
super admin session can change settings, a lot above the EA's reported
hard limit is refused, every change is versioned and audited (with turning
live called out), the feed delivers the settings, and a terminal's report
headers are recorded without ever failing a poll.
"""

from collections.abc import Generator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.ea_token import EaToken
from app.models.enums import MarketType, UserRole
from app.models.signal import Signal
from app.models.user import User

_TABLES = [
    User.__table__,
    EaToken.__table__,
    AuditLog.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
]

_DEFAULTS = {
    "paused": False,
    "dry_run": True,
    "lot_size": 0.01,
    "max_open_trades": 1,
    "max_slippage_points": 50,
}


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
def client(session_engine: object, db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        s = Session(session_engine)  # type: ignore[arg-type]
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    db.add(Asset(symbol="XAUUSD", name="Gold / US Dollar", market_type=MarketType.METAL))
    db.commit()
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


def _token(client: TestClient, user: User) -> dict[str, Any]:
    _as(user)
    response = client.post("/api/v1/ea/tokens", json={"name": "Windows Server"})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _save(client: TestClient, token_id: str, **overrides: Any) -> httpx.Response:
    return client.put(f"/api/v1/ea/tokens/{token_id}/settings", json={**_DEFAULTS, **overrides})


def _poll(client: TestClient, raw: str, **headers: str) -> httpx.Response:
    return client.get(
        "/api/v1/ea/signals",
        params={"symbol": "XAUUSD"},
        headers={"X-EA-Token": raw, **headers},
    )


def _listed(client: TestClient, user: User) -> dict[str, Any]:
    _as(user)
    [item] = client.get("/api/v1/ea/tokens").json()["items"]
    result: dict[str, Any] = item
    return result


def test_a_new_token_has_the_eas_own_defaults(client: TestClient, db: Session) -> None:
    """An unconfigured token must change nothing about how its EA runs."""
    body = _token(client, _user(db))

    assert {k: body["settings"][k] for k in _DEFAULTS} == _DEFAULTS
    assert body["settings"]["version"] == 1
    assert set(body["terminal"].values()) == {None}


def test_saving_settings_bumps_the_version_and_audits_it(client: TestClient, db: Session) -> None:
    token = _token(client, _user(db))

    response = _save(client, token["id"], lot_size=0.05, dry_run=False)

    assert response.status_code == 200, response.text
    assert response.json()["settings"]["lot_size"] == 0.05
    assert response.json()["settings"]["version"] == 2
    [entry] = db.query(AuditLog).filter_by(action="ea_settings_updated").all()
    assert entry.context is not None
    assert entry.context["changes"]["lot_size"] == {"from": "0.01", "to": "0.05"}
    assert entry.context["live_requested"] is True


def test_resaving_identical_settings_is_a_no_op(client: TestClient, db: Session) -> None:
    """Otherwise re-saving an unchanged form would make the terminal look
    out of date until its next poll."""
    token = _token(client, _user(db))

    response = _save(client, token["id"])

    assert response.json()["settings"]["version"] == 1
    assert db.query(AuditLog).filter_by(action="ea_settings_updated").count() == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"lot_size": 0.015},
        {"lot_size": 0},
        {"max_open_trades": 0},
        {"max_open_trades": 21},
        {"max_slippage_points": -1},
    ],
)
def test_invalid_settings_are_refused(
    client: TestClient, db: Session, overrides: dict[str, Any]
) -> None:
    token = _token(client, _user(db))

    assert _save(client, token["id"], **overrides).status_code == 422


def test_a_lot_above_the_eas_hard_limit_is_refused(client: TestClient, db: Session) -> None:
    """The EA enforces MaxLotSize itself; refusing here too means the
    operator is told now, not left wondering why the EA traded less."""
    user = _user(db)
    token = _token(client, user)
    _logout()
    _poll(client, token["token"], **{"X-EA-Version": "1.20", "X-EA-Max-Lot": "0.10"})

    _as(user)
    refused = _save(client, token["id"], lot_size=0.2)
    allowed = _save(client, token["id"], lot_size=0.1)

    assert refused.status_code == 422
    assert "0.10" in refused.json()["message"]
    assert allowed.status_code == 200


def test_the_feed_delivers_the_saved_settings(client: TestClient, db: Session) -> None:
    user = _user(db)
    token = _token(client, user)
    _save(client, token["id"], paused=True, max_open_trades=3)
    _logout()

    settings = _poll(client, token["token"]).json()["settings"]

    assert settings["paused"] is True
    assert settings["max_open_trades"] == 3
    assert settings["version"] == 2


def test_the_terminals_report_is_recorded(client: TestClient, db: Session) -> None:
    user = _user(db)
    token = _token(client, user)
    _logout()

    response = _poll(
        client,
        token["token"],
        **{
            "X-EA-Version": "1.20",
            "X-EA-Max-Lot": "0.10",
            "X-EA-Allow-Live": "0",
            "X-EA-Settings-Version": "1",
            "X-EA-Dry-Run": "1",
            "X-EA-Paused": "0",
        },
    )

    assert response.status_code == 200
    assert _listed(client, user)["terminal"] == {
        "ea_version": "1.20",
        "max_lot": 0.1,
        "allow_remote_live": False,
        "applied_settings_version": 1,
        "dry_run": True,
        "paused": False,
    }


def test_garbled_report_headers_never_fail_a_poll(client: TestClient, db: Session) -> None:
    """The feed is what the EA trades from - a bad self-report header must
    not cost it its signals."""
    user = _user(db)
    token = _token(client, user)
    _logout()

    response = _poll(
        client,
        token["token"],
        **{"X-EA-Max-Lot": "lots", "X-EA-Allow-Live": "maybe", "X-EA-Settings-Version": "-2"},
    )

    assert response.status_code == 200
    terminal = _listed(client, user)["terminal"]
    assert terminal["max_lot"] is None
    assert terminal["allow_remote_live"] is None
    assert terminal["applied_settings_version"] is None


def test_an_out_of_range_settings_version_is_ignored(client: TestClient, db: Session) -> None:
    """The column is a 32-bit integer on Postgres. Storing a larger number
    would fail the commit and turn the EA's poll into a 500."""
    user = _user(db)
    token = _token(client, user)
    _logout()

    response = _poll(client, token["token"], **{"X-EA-Settings-Version": "99999999999"})

    assert response.status_code == 200
    assert _listed(client, user)["terminal"]["applied_settings_version"] is None


def test_a_poll_without_report_headers_keeps_the_last_report(
    client: TestClient, db: Session
) -> None:
    """Event reports (and an EA 1.10) authenticate without these headers;
    that must not wipe what the terminal said on its last feed poll."""
    user = _user(db)
    token = _token(client, user)
    _logout()
    _poll(client, token["token"], **{"X-EA-Version": "1.20", "X-EA-Max-Lot": "0.10"})

    _poll(client, token["token"])

    assert _listed(client, user)["terminal"]["max_lot"] == 0.1


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.REGISTERED])
def test_only_a_super_admin_can_change_settings(
    client: TestClient, db: Session, role: UserRole
) -> None:
    token = _token(client, _user(db))

    _as(_user(db, "someone", role))

    assert _save(client, token["id"], lot_size=0.05).status_code == 403


def test_another_users_token_is_404(client: TestClient, db: Session) -> None:
    token = _token(client, _user(db, "owner"))

    _as(_user(db, "other"))

    assert _save(client, token["id"], lot_size=0.05).status_code == 404


def test_an_ea_token_cannot_change_its_own_settings(client: TestClient, db: Session) -> None:
    """Settings flow website -> terminal only. A terminal that could write
    them could lift its own limits."""
    token = _token(client, _user(db))
    _logout()

    response = client.put(
        f"/api/v1/ea/tokens/{token['id']}/settings",
        json={**_DEFAULTS, "dry_run": False},
        headers={"X-EA-Token": token["token"]},
    )

    assert response.status_code == 401

"""ADR-184 - the server-side one-live-order canary.

Driven through the real routes: the admin arms it with PUT
/admin/runtime-settings, the EA reports through POST /ea/events, and the EA
reads its settings back from GET /ea/signals - the same round trip the
terminal makes. Telegram and the website push are replaced by recorders.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

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
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.services import runtime_settings
from app.services.ea_canary import CANARY_SETTING
from app.services.ea_service import EaService

_TABLES = [
    User.__table__, EaToken.__table__, AuditLog.__table__, Asset.__table__,
    AIAnalysis.__table__, Signal.__table__, EaExecutionEvent.__table__,
    SystemSetting.__table__,
]
_KEY = runtime_settings.storage_key(CANARY_SETTING)
_LIVE = {"paused": False, "dry_run": False, "lot_size": 0.03,
         "max_open_trades": 2, "max_slippage_points": 30}


@pytest.fixture
def engine() -> Generator[object, None, None]:
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    Base.metadata.create_all(eng, tables=_TABLES)
    yield eng


@pytest.fixture(autouse=True)
def quiet(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """No Celery, no Redis; and the shared settings object is restored
    afterwards, since arming and tripping write through to it."""
    monkeypatch.setattr(ea_routes, "enqueue_ea_event_delivery", lambda *_: None)
    monkeypatch.setattr(ea_routes, "publish_signal_status_changed", lambda *_: None)
    monkeypatch.setattr(ea_routes, "enqueue_signal_triggered_delivery", lambda *_: None)
    monkeypatch.setattr(ea_routes, "enqueue_signal_outcome_delivery", lambda *_: None)
    yield
    runtime_settings.refresh(force=True, loader=lambda: {})


def _client(engine: object) -> TestClient:
    def override_get_db() -> Generator[Session, None, None]:
        s = Session(engine)  # type: ignore[arg-type]
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def client(engine: object) -> Generator[TestClient, None, None]:
    with _client(engine) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db(engine: object) -> Generator[Session, None, None]:
    with Session(engine) as s:  # type: ignore[arg-type]
        yield s


def _admin(db: Session) -> User:
    user = User(email="root@example.com", username="root", password_hash="x",
                role=UserRole.SUPER_ADMIN, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _live_token(client: TestClient, user: User, **settings: Any) -> dict[str, Any]:
    """A token switched to live trading from the Settings page."""
    _as(user)
    token: dict[str, Any] = client.post("/api/v1/ea/tokens", json={"name": "VcEA"}).json()
    response = client.put(f"/api/v1/ea/tokens/{token['id']}/settings",
                          json={**_LIVE, **settings})
    assert response.status_code == 200, response.text
    return token


def _arm(client: TestClient, user: User, on: bool = True) -> None:
    _as(user)
    response = client.put("/api/v1/admin/runtime-settings",
                          json={"changes": {CANARY_SETTING: on}})
    assert response.status_code == 200, response.text


def _signal(db: Session) -> Signal:
    asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL)
    db.add(asset)
    db.commit()
    signal = Signal(
        analysis_id=uuid.uuid4(), asset_id=asset.id, timeframe=Timeframe.M5,
        signal_type=SignalType.BUY, entry_price=Decimal("4114.67"),
        stop_loss=Decimal("4111.70"), take_profit=Decimal("4160.25"), risk_reward=15.3,
        confidence=0.0, strategy="smc_ict_crt_v1", status=SignalStatus.ACTIVE,
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def _event(signal: Signal, key: str, event_type: str, *, dry_run: bool = False) -> dict[str, Any]:
    return {
        "event_key": key, "event_type": event_type, "signal_id": str(signal.id),
        "dry_run": dry_run, "occurred_at": int(datetime.now(UTC).timestamp()),
        "account_login": "160018306", "broker_symbol": "XAUUSDc", "order_type": "buy_limit",
        "volume": 0.03, "price": 4114.67, "stop_loss": 4111.7, "take_profit": 4160.25,
        "retcode": 0, "message": None,
    }


def _report(client: TestClient, raw: str, *events: dict[str, Any]) -> Any:
    return client.post("/api/v1/ea/events",
                       json={"events": list(events)}, headers={"X-EA-Token": raw})


def _feed_settings(client: TestClient, raw: str) -> dict[str, Any]:
    response = client.get("/api/v1/ea/signals", params={"symbol": "XAUUSD"},
                          headers={"X-EA-Token": raw})
    assert response.status_code == 200, response.text
    settings: dict[str, Any] = response.json()["settings"]
    return settings


def _armed(db: Session) -> bool | None:
    db.expire_all()
    row = db.query(SystemSetting).filter_by(key=_KEY).one_or_none()
    return None if row is None else row.value == "true"


def _audits(db: Session, action: str) -> list[AuditLog]:
    db.expire_all()
    return db.query(AuditLog).filter_by(action=action).order_by(AuditLog.created_at).all()


# --- 1. armed + order_placed ------------------------------------------------
def test_armed_first_live_order_reverts_to_dry_run_disarms_and_audits(
    client: TestClient, db: Session
) -> None:
    admin = _admin(db)
    token = _live_token(client, admin)
    signal = _signal(db)
    _arm(client, admin)
    before = _feed_settings(client, token["token"])
    assert before["dry_run"] is False and _armed(db) is True

    response = _report(client, token["token"], _event(signal, "placed:1", "order_placed"))
    assert response.status_code == 200, response.text

    after = _feed_settings(client, token["token"])     # what the EA reads next poll
    assert after["dry_run"] is True
    assert after["version"] == before["version"] + 1
    assert _armed(db) is False                         # auto-disarmed

    [reverted] = [a for a in _audits(db, "ea_settings_updated")
                  if a.context["changes"].get("dry_run") == {"from": False, "to": True}]
    assert reverted.context["live_requested"] is False
    trip = [a for a in _audits(db, "runtime_setting_changed")
            if a.context.get("reason", "").startswith("tripped")]
    assert len(trip) == 1 and trip[0].user_id is None
    assert trip[0].context["old"] == "true" and trip[0].context["new"] == "false"
    assert trip[0].context["event_type"] == "order_placed"


# --- 2. armed + position_opened without order_placed ------------------------
def test_a_live_fill_alone_trips_it_too(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    token = _live_token(client, admin)
    signal = _signal(db)
    _arm(client, admin)

    _report(client, token["token"], _event(signal, "opened:1", "position_opened"))

    assert _feed_settings(client, token["token"])["dry_run"] is True
    assert _armed(db) is False


# --- 3. a second live event does nothing more ------------------------------
def test_a_second_live_event_takes_no_second_action(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    token = _live_token(client, admin)
    signal = _signal(db)
    _arm(client, admin)
    _report(client, token["token"], _event(signal, "placed:1", "order_placed"))
    version = _feed_settings(client, token["token"])["version"]
    audits = len(_audits(db, "ea_settings_updated")) + len(_audits(db, "runtime_setting_changed"))

    _report(client, token["token"], _event(signal, "opened:1", "position_opened"),
            _event(signal, "placed:2", "order_placed"))

    assert _feed_settings(client, token["token"])["version"] == version
    assert len(_audits(db, "ea_settings_updated")) + len(
        _audits(db, "runtime_setting_changed")) == audits


# --- 4. dry-run events are ignored -----------------------------------------
def test_dry_run_reports_never_trip_it(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    token = _live_token(client, admin)
    signal = _signal(db)
    _arm(client, admin)

    _report(client, token["token"],
            _event(signal, "placed:dry", "order_placed", dry_run=True),
            _event(signal, "opened:dry", "position_opened", dry_run=True),
            _event(signal, "check:1", "dry_run_checked", dry_run=True))

    assert _feed_settings(client, token["token"])["dry_run"] is False
    assert _armed(db) is True


# --- 5. canary off: behaviour unchanged ------------------------------------
@pytest.mark.parametrize("state", ["never_set", "turned_off"])
def test_with_the_canary_off_nothing_changes(
    client: TestClient, db: Session, state: str
) -> None:
    admin = _admin(db)
    token = _live_token(client, admin)
    signal = _signal(db)
    if state == "turned_off":
        _arm(client, admin)
        _arm(client, admin, on=False)
    version = _feed_settings(client, token["token"])["version"]

    _report(client, token["token"], _event(signal, "placed:1", "order_placed"))

    settings = _feed_settings(client, token["token"])
    assert settings["dry_run"] is False and settings["version"] == version


# --- 6. every other setting is preserved -----------------------------------
def test_every_other_setting_is_kept(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    token = _live_token(client, admin, lot_size=0.05, max_open_trades=3,
                        max_slippage_points=40)
    signal = _signal(db)
    _arm(client, admin)

    _report(client, token["token"], _event(signal, "placed:1", "order_placed"))

    after = _feed_settings(client, token["token"])
    assert after["dry_run"] is True
    assert (after["paused"], after["lot_size"], after["max_open_trades"],
            after["max_slippage_points"]) == (False, 0.05, 3, 40)


def test_the_lot_is_capped_at_the_terminals_max_lot(client: TestClient, db: Session) -> None:
    """update_settings refuses a lot above MaxLotSize; the revert must not
    fail because of it (ea_revert.py's rule)."""
    admin = _admin(db)
    token = _live_token(client, admin, lot_size=0.05)
    signal = _signal(db)
    _arm(client, admin)
    row = db.get(EaToken, uuid.UUID(token["id"]))
    row.ea_max_lot = Decimal("0.01")               # terminal lowered MaxLotSize since
    db.commit()

    _report(client, token["token"], _event(signal, "placed:1", "order_placed"))

    after = _feed_settings(client, token["token"])
    assert after["dry_run"] is True and after["lot_size"] == 0.01


def test_a_token_already_in_dry_run_still_disarms(client: TestClient, db: Session) -> None:
    """update_settings is a no-op for an unchanged token; the disarm must
    still be committed."""
    admin = _admin(db)
    _as(admin)
    token = client.post("/api/v1/ea/tokens", json={"name": "VcEA"}).json()  # dry run
    signal = _signal(db)
    _arm(client, admin)

    _report(client, token["token"], _event(signal, "placed:1", "order_placed"))

    assert _armed(db) is False
    assert _feed_settings(client, token["token"])["dry_run"] is True


# --- failure and restart ----------------------------------------------------
def test_a_failed_trip_is_retried_by_the_eas_resend(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If tripping fails after the events are stored, the error makes the EA
    re-send the batch; the re-send is all duplicates, and still trips it."""
    admin = _admin(db)
    token = _live_token(client, admin)
    signal = _signal(db)
    _arm(client, admin)
    original = EaService.update_settings
    calls = {"n": 0}

    def flaky(self: EaService, *args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("database went away")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(EaService, "update_settings", flaky)
    batch = _event(signal, "placed:1", "order_placed")
    with pytest.raises(RuntimeError):
        _report(client, token["token"], batch)
    assert _armed(db) is True                         # the failed attempt changed nothing
    db.expire_all()
    assert db.query(EaExecutionEvent).count() == 1    # but the event itself was kept

    retry = _report(client, token["token"], batch)
    assert retry.status_code == 200 and retry.json()["duplicates"] == 1
    assert _feed_settings(client, token["token"])["dry_run"] is True
    assert _armed(db) is False


def test_the_armed_state_survives_a_restart(engine: object, db: Session) -> None:
    """Armed is a database row, not process memory: a fresh app process -
    empty settings cache - still trips on the first live order."""
    admin = _admin(db)
    with _client(engine) as first:
        token = _live_token(first, admin)
        _arm(first, admin)
    app.dependency_overrides.clear()
    runtime_settings.refresh(force=True, loader=lambda: {})   # the new process knows nothing
    signal = _signal(db)

    with _client(engine) as restarted:
        _report(restarted, token["token"], _event(signal, "placed:1", "order_placed"))
        assert _feed_settings(restarted, token["token"])["dry_run"] is True
    app.dependency_overrides.clear()
    assert _armed(db) is False


def test_the_canary_row_is_read_under_a_postgres_row_lock(db: Session) -> None:
    """Two batches reported at once must trip it once: the read is SELECT
    ... FOR UPDATE on PostgreSQL (SQLite, used here, ignores the lock, so
    the SQL itself is what is checked)."""
    from sqlalchemy.dialects import postgresql

    from app.repositories.system_setting_repository import SystemSettingRepository

    captured: list[Any] = []

    class _Recorder:
        def execute(self, query: Any) -> Any:
            captured.append(query)
            raise StopIteration

    repo = SystemSettingRepository(db)
    repo.session = _Recorder()  # type: ignore[assignment]
    with pytest.raises(StopIteration):
        repo.get_by_key_for_update(_KEY)
    sql = str(captured[0].compile(dialect=postgresql.dialect()))
    assert sql.rstrip().endswith("FOR UPDATE")

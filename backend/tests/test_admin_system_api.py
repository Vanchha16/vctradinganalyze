"""API-level tests for Phase 7D-C (docs/58 §3.2, ADR-130). Mirrors
`test_admin_logs_api.py`'s pattern: a real `TestClient` against the
actual app/router, `get_current_user` overridden per test to simulate
different actor roles, and a shared in-memory SQLite database.

`conftest.py` already forces every provider list to `["mock"]` and
blanks every real API key, and blocks any non-loopback socket - the two
ingestion-triggering tests below exercise `MockNewsProvider`/
`MockEconomicCalendarProvider` exclusively, never a real vendor.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.economic_event import EconomicEvent
from app.models.enums import MarketType, Recommendation, SignalType, Timeframe, UserRole
from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.models.news_source import NewsSource
from app.models.signal import Signal
from app.models.user import User
from app.models.user_session import UserSession

_TABLES = [
    User.__table__,
    UserSession.__table__,
    AuditLog.__table__,
    Asset.__table__,
    AIAnalysis.__table__,
    Signal.__table__,
    NewsSource.__table__,
    NewsArticle.__table__,
    NewsSentiment.__table__,
    EconomicEvent.__table__,
]

_PASSWORD = "Correct-Horse9"


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    return engine


@pytest.fixture
def client(engine) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_user(engine, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": "user@example.com",
        "username": "user",
        "password_hash": hash_password(_PASSWORD),
        "role": UserRole.REGISTERED,
    }
    defaults.update(overrides)
    with Session(engine) as session:
        user = User(**defaults)
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _make_session(engine, user: User) -> UserSession:
    with Session(engine) as session:
        row = UserSession(
            user_id=user.id,
            refresh_token_hash="hash",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        session.expunge(row)
        return row


def _make_asset(engine, symbol: str = "EURUSD") -> Asset:
    with Session(engine) as session:
        asset = Asset(symbol=symbol, name="Euro / US Dollar", market_type=MarketType.FOREX)
        session.add(asset)
        session.commit()
        session.refresh(asset)
        session.expunge(asset)
        return asset


def _make_signal(engine, asset: Asset, *, signal_type: SignalType = SignalType.BUY) -> Signal:
    with Session(engine) as session:
        analysis = AIAnalysis(
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            recommendation=(
                Recommendation.BUY if signal_type == SignalType.BUY else Recommendation.SELL
            ),
            confidence_score=80.0,
            confidence_level="high",
            reasoning={},
            supporting_evidence=[],
            model_name="mock",
            prompt_version="1.0.0",
        )
        session.add(analysis)
        session.flush()
        signal = Signal(
            analysis_id=analysis.id,
            asset_id=asset.id,
            timeframe=Timeframe.H1,
            signal_type=signal_type,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("115"),
            risk_reward=3.0,
            confidence=80.0,
        )
        session.add(signal)
        session.commit()
        session.refresh(signal)
        session.expunge(signal)
        return signal


def _act_as(client: TestClient, actor: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: actor


# --- Authorization (every endpoint) -------------------------------------


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "/api/v1/admin/signals", None),
        ("get", "/api/v1/admin/system", None),
        ("get", "/api/v1/admin/analytics", None),
        ("post", "/api/v1/admin/news", None),
        ("post", "/api/v1/admin/maintenance", {"action": "refresh_news"}),
    ],
)
def test_endpoint_rejects_non_admin(
    client: TestClient, engine, method: str, path: str, body: dict | None
) -> None:
    registered = _make_user(engine, email="reg@example.com", username="reg")
    _act_as(client, registered)

    response = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)

    assert response.status_code == 403
    assert response.json()["error"] == "insufficient_role"


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "/api/v1/admin/signals", None),
        ("get", "/api/v1/admin/system", None),
        ("get", "/api/v1/admin/analytics", None),
        ("post", "/api/v1/admin/news", None),
        ("post", "/api/v1/admin/maintenance", {"action": "refresh_news"}),
    ],
)
def test_endpoint_rejects_unauthenticated(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)

    assert response.status_code == 401


# --- GET /admin/signals ---------------------------------------------------


def test_list_admin_signals_pagination_and_total(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine)
    for _ in range(3):
        _make_signal(engine, asset)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/signals", params={"page": 1, "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["symbol"] == "EURUSD"


def test_list_admin_signals_returns_signals_regardless_of_who_created_them(
    client: TestClient, engine
) -> None:
    """docs/58 §3.2's "all users, not just caller's" - `Signal` has no
    `user_id` (ADR-130), so this is inherently unscoped; confirm the
    admin sees a signal even though no user "owns" it."""
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine)
    _make_signal(engine, asset)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/signals")

    assert response.status_code == 200
    assert response.json()["total"] == 1


# --- GET /admin/system ----------------------------------------------------


def test_admin_system_status_returns_ok_with_today_counts(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    asset = _make_asset(engine)
    _make_signal(engine, asset)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/system")

    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["redis"] in ("ok", "down")  # real local Redis may or may not be running
    assert body["signals_today"] == 1
    assert body["ai_analyses_today"] == 1


def test_admin_system_status_degrades_gracefully_when_redis_is_unreachable(
    client: TestClient, engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Must return 200 with `redis: "down"`, never 500 (§3.2)."""
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    monkeypatch.setattr(
        "app.config.settings.redis_url", "redis://127.0.0.1:1/0"
    )  # unreachable Redis DB index/port

    response = client.get("/api/v1/admin/system")

    assert response.status_code == 200
    assert response.json()["redis"] == "down"
    assert response.json()["database"] == "ok"


# --- GET /admin/analytics --------------------------------------------------


def test_admin_analytics_empty_case(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["daily_active_users"] == 0
    assert body["signal_type_distribution"] == {}


def test_admin_analytics_dau_and_distribution(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    alice = _make_user(engine, email="alice@example.com", username="alice")
    _make_session(engine, admin)
    _make_session(engine, alice)
    _make_session(engine, alice)  # a second login by the same user must not double-count DAU

    asset = _make_asset(engine)
    _make_signal(engine, asset, signal_type=SignalType.BUY)
    _make_signal(engine, asset, signal_type=SignalType.BUY)
    _make_signal(engine, asset, signal_type=SignalType.SELL)
    _act_as(client, admin)

    response = client.get("/api/v1/admin/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["daily_active_users"] == 2
    assert body["signal_type_distribution"] == {"buy": 2, "sell": 1}


# --- POST /admin/news, POST /admin/maintenance ----------------------------


def test_refresh_news_ingests_and_writes_audit_row(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post("/api/v1/admin/news")

    assert response.status_code == 200
    assert response.json()["articles_ingested"] >= 0

    with Session(engine) as session:
        logs = session.query(AuditLog).filter_by(action="admin_news_refreshed").all()
        assert len(logs) == 1
        assert logs[0].user_id == admin.id


def test_maintenance_refresh_news_shares_the_same_implementation(
    client: TestClient, engine
) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post("/api/v1/admin/maintenance", json={"action": "refresh_news"})

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "refresh_news"
    assert body["news"]["articles_ingested"] >= 0
    assert body["calendar"] is None

    with Session(engine) as session:
        logs = session.query(AuditLog).filter_by(action="admin_news_refreshed").all()
        assert len(logs) == 1
        assert logs[0].user_id == admin.id


def test_maintenance_refresh_calendar_ingests_and_writes_audit_row(
    client: TestClient, engine
) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post("/api/v1/admin/maintenance", json={"action": "refresh_calendar"})

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "refresh_calendar"
    assert body["calendar"]["events_created"] + body["calendar"]["events_updated"] > 0
    assert body["news"] is None

    with Session(engine) as session:
        logs = session.query(AuditLog).filter_by(action="admin_calendar_refreshed").all()
        assert len(logs) == 1
        assert logs[0].user_id == admin.id


def test_maintenance_rejects_unknown_action(client: TestClient, engine) -> None:
    admin = _make_user(engine, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _act_as(client, admin)

    response = client.post("/api/v1/admin/maintenance", json={"action": "restart_workers"})

    assert response.status_code == 422

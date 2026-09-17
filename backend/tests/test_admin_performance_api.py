"""API-level tests for `GET /admin/performance` (ADR-174).

Mirrors `test_admin_logs_api.py`: a real `TestClient` against the actual
app/router, `get_current_user` overridden per test, shared in-memory
SQLite.

**What these tests are actually for.** This endpoint is arithmetic over a
table that already exists. The risk is not that it fails to run - it is
that it runs and reports plausible, wrong numbers. The two traps below
have each bitten this project once already, so they are tested first and
by name:

1. Rows created before `signal_metrics_epoch` carry outcomes current code
   cannot produce (stored SUCCESSFUL with `triggered_at IS NULL`).
   Counted in, they drag the BUY fill rate from 56% to 14%.
2. Open/expired/closed is computed at read time (ADR-088). Reading the
   stored column instead is the bug in BACKLOG.md where an unfilled
   signal past its TTL showed as active and never as expired.

Every other test pins one metric against a hand-computed fixture, because
a win rate over 3 trades and one over 300 render identically.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.security import hash_password
from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import (
    MarketType,
    Recommendation,
    SignalStatus,
    SignalType,
    Timeframe,
    UserRole,
)
from app.models.signal import Signal
from app.models.user import User
from app.services.signal_confirmation_service import REPLACED_REASON

_TABLES = [User.__table__, Asset.__table__, AIAnalysis.__table__, Signal.__table__]

_EPOCH = settings.signal_metrics_epoch
#: Comfortably after the epoch, and recent enough that a signal seeded
#: here is still inside both TTLs unless a test deliberately backdates it.
_NOW = datetime.now(UTC)
_RECENT = _NOW - timedelta(hours=1)
#: Before the epoch: the 2026-08-05..07 window whose rows predate ADR-137.
_PRE_EPOCH = _EPOCH - timedelta(days=1)


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
        "email": "admin@example.com",
        "username": "admin",
        "password_hash": hash_password("Correct-Horse9"),
        "role": UserRole.ADMIN,
    }
    defaults.update(overrides)
    with Session(engine) as session:
        user = User(**defaults)
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _act_as(client: TestClient, actor: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: actor


def _asset(engine) -> uuid.UUID:
    with Session(engine) as session:
        existing = session.query(Asset).first()
        if existing is not None:
            return existing.id
        asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL)
        session.add(asset)
        session.commit()
        return asset.id


def _analysis(engine, asset_id: uuid.UUID, verdict: str | None = None) -> uuid.UUID:
    with Session(engine) as session:
        analysis = AIAnalysis(
            asset_id=asset_id,
            timeframe=Timeframe.H1,
            recommendation=Recommendation.BUY,
            confidence_score=75.0,
            confidence_level="high",
            reasoning={},
            supporting_evidence=[],
            conflicting_evidence=[],
            risks=[],
            invalidation_conditions=[],
            model_name="test",
            prompt_version="v1",
            warnings=[],
            risk_review_verdict=verdict,
        )
        session.add(analysis)
        session.commit()
        return analysis.id


def _signal(
    engine,
    *,
    status: SignalStatus = SignalStatus.SUCCESSFUL,
    created_at: datetime | None = None,
    triggered_at: datetime | None = _RECENT,
    profit_loss: str | None = "10",
    signal_type: SignalType = SignalType.BUY,
    timeframe: Timeframe = Timeframe.H1,
    strategy: str | None = "smc",
    confidence: float = 75.0,
    verdict: str | None = None,
    status_reason: str | None = None,
) -> None:
    asset_id = _asset(engine)
    with Session(engine) as session:
        session.add(
            Signal(
                analysis_id=_analysis(engine, asset_id, verdict),
                asset_id=asset_id,
                timeframe=timeframe,
                signal_type=signal_type,
                entry_price=Decimal("4000"),
                stop_loss=Decimal("3990"),
                take_profit=Decimal("4020"),
                risk_reward=2.0,
                confidence=confidence,
                strategy=strategy,
                status=status,
                created_at=created_at or _RECENT,
                triggered_at=triggered_at,
                profit_loss=Decimal(profit_loss) if profit_loss is not None else None,
                status_reason=status_reason,
            )
        )
        session.commit()


def _get(client: TestClient, engine) -> dict:
    _act_as(client, _make_user(engine))
    response = client.get("/api/v1/admin/performance")
    assert response.status_code == 200, response.text
    return response.json()


# --- Trap 1: pre-epoch rows ----------------------------------------------


def test_pre_epoch_signals_are_excluded_from_every_count(client: TestClient, engine) -> None:
    """The §1.1 trap: a stored SUCCESSFUL with `triggered_at IS NULL`, a
    state current code cannot produce. Counted in, it inflates wins and
    halves the fill rate."""
    _signal(
        engine,
        status=SignalStatus.SUCCESSFUL,
        created_at=_PRE_EPOCH,
        triggered_at=None,
        profit_loss="999",
    )

    body = _get(client, engine)

    assert body["overall"]["trades"] == 0
    assert body["overall"]["wins"] == 0
    assert body["overall"]["total_points"] is None
    assert body["fills"] == {"created": 0, "filled": 0, "fill_rate": None}
    assert body["by_strategy"] == []


def test_the_epoch_boundary_is_inclusive(client: TestClient, engine) -> None:
    """`created_at >= epoch`. A signal created exactly at the epoch is
    counted - the cut is "before the fix", not "before the day after"."""
    _signal(engine, created_at=_EPOCH, triggered_at=_EPOCH + timedelta(minutes=5))

    assert _get(client, engine)["overall"]["trades"] == 1


# --- Trap 2: read-time status --------------------------------------------


def test_an_unfilled_signal_past_its_ttl_reads_as_expired_not_active(
    client: TestClient, engine
) -> None:
    """The §1.2 trap, and the exact bug recorded in BACKLOG.md."""
    stale = _NOW - timedelta(hours=settings.signal_ttl_hours + 1)
    _signal(
        engine, status=SignalStatus.ACTIVE, created_at=stale, triggered_at=None, profit_loss=None
    )

    open_state = _get(client, engine)["open_state"]

    assert open_state["active"] == 0
    assert open_state["expired"] == 1


def test_a_live_trade_past_its_ttl_is_closed_counted_and_never_a_win_or_loss(
    client: TestClient, engine
) -> None:
    """A TRIGGERED signal past `signal_triggered_ttl_hours` reached neither
    target. It is a real filled trade - it must stay in `trades` - but it
    has no P&L, so it is neither a win nor a loss, and `wins + losses` is
    legitimately less than `trades`."""
    filled_long_ago = _NOW - timedelta(hours=settings.signal_triggered_ttl_hours + 1)
    _signal(
        engine,
        status=SignalStatus.TRIGGERED,
        created_at=filled_long_ago,
        triggered_at=filled_long_ago,
        profit_loss=None,
    )

    body = _get(client, engine)

    assert body["overall"]["trades"] == 1
    assert body["overall"]["wins"] == 0
    assert body["overall"]["losses"] == 0
    assert body["overall"]["win_rate"] is None
    assert body["closed_without_outcome"] == 1
    assert body["open_state"]["closed"] == 1
    assert body["open_state"]["triggered"] == 0


# --- The arithmetic ------------------------------------------------------


def test_metrics_against_a_hand_computed_fixture(client: TestClient, engine) -> None:
    """Two wins (+30, +10) and one loss (-20) over three filled trades."""
    _signal(engine, status=SignalStatus.SUCCESSFUL, profit_loss="30")
    _signal(engine, status=SignalStatus.SUCCESSFUL, profit_loss="10")
    _signal(engine, status=SignalStatus.STOPPED_OUT, profit_loss="-20")

    overall = _get(client, engine)["overall"]

    assert overall["trades"] == 3
    assert (overall["wins"], overall["losses"]) == (2, 1)
    assert overall["win_rate"] == pytest.approx(2 / 3)
    assert Decimal(overall["total_points"]) == Decimal("20")
    assert Decimal(overall["avg_win"]) == Decimal("20")
    assert Decimal(overall["avg_loss"]) == Decimal("-20")
    assert Decimal(overall["expectancy"]) == Decimal("20") / 3
    assert overall["profit_factor"] == pytest.approx(40 / 20)


def test_every_ratio_is_null_not_zero_when_its_denominator_is_zero(
    client: TestClient, engine
) -> None:
    """A 0% win rate and "no trades yet" are different facts, and the UI
    must be able to tell them apart."""
    body = _get(client, engine)
    overall = body["overall"]

    assert overall["trades"] == 0
    assert overall["win_rate"] is None
    assert overall["expectancy"] is None
    assert overall["profit_factor"] is None
    assert overall["avg_win"] is None
    assert overall["avg_loss"] is None
    assert overall["total_points"] is None
    assert body["fills"]["fill_rate"] is None


def test_profit_factor_is_null_when_losses_sum_to_zero(client: TestClient, engine) -> None:
    """Nothing to divide by is not the same as an infinitely good
    strategy."""
    _signal(engine, status=SignalStatus.SUCCESSFUL, profit_loss="30")

    overall = _get(client, engine)["overall"]

    assert overall["wins"] == 1
    assert overall["losses"] == 0
    assert overall["profit_factor"] is None
    assert overall["win_rate"] == 1.0


def test_fill_rate_counts_created_against_filled(client: TestClient, engine) -> None:
    _signal(engine, status=SignalStatus.SUCCESSFUL, profit_loss="10")
    _signal(engine, status=SignalStatus.ACTIVE, triggered_at=None, profit_loss=None)
    _signal(engine, status=SignalStatus.ACTIVE, triggered_at=None, profit_loss=None)

    fills = _get(client, engine)["fills"]

    assert fills["created"] == 3
    assert fills["filled"] == 1
    assert fills["fill_rate"] == pytest.approx(1 / 3)


# --- Breakdowns ----------------------------------------------------------


def test_every_breakdown_row_carries_its_own_trades_count(client: TestClient, engine) -> None:
    """A rate without its denominator is not a result."""
    _signal(engine, strategy="smc", timeframe=Timeframe.H1, signal_type=SignalType.BUY)
    _signal(engine, strategy="breakout", timeframe=Timeframe.M15, signal_type=SignalType.SELL)

    body = _get(client, engine)

    for name in ("by_strategy", "by_timeframe", "by_signal_type", "by_confidence"):
        rows = body[name]
        assert rows, f"{name} was empty"
        for row in rows:
            assert "trades" in row["metrics"]
            assert row["metrics"]["trades"] >= 1


def test_breakdown_keys_render_as_plain_values_not_enum_reprs(client: TestClient, engine) -> None:
    _signal(engine, timeframe=Timeframe.H1, signal_type=SignalType.BUY, strategy="smc")

    body = _get(client, engine)

    # `Timeframe.H1.value` is lowercase "h1" - the stored value, not the
    # member name, which is what a JSON consumer should see.
    assert [row["key"] for row in body["by_timeframe"]] == ["h1"]
    assert [row["key"] for row in body["by_signal_type"]] == ["buy"]
    assert [row["key"] for row in body["by_strategy"]] == ["smc"]


def test_a_signal_with_no_strategy_is_its_own_group_not_a_dropped_row(
    client: TestClient, engine
) -> None:
    """Signals predating the `strategy` column are a real group. Dropping
    them would make the breakdown disagree with the total."""
    _signal(engine, strategy=None)

    body = _get(client, engine)

    assert body["by_strategy"] == [{"key": None, "metrics": body["by_strategy"][0]["metrics"]}]
    assert body["by_strategy"][0]["metrics"]["trades"] == body["overall"]["trades"] == 1


def test_confidence_bands_split_trades_by_band(client: TestClient, engine) -> None:
    """`confidence` is a 0-100 score, not a 0-1 fraction - the values here
    are real ones from the dev database. Banded as 0-1, every trade lands
    outside every band and the breakdown renders empty but healthy, which
    is exactly how this shipped wrong the first time."""
    _signal(engine, confidence=56.18)
    _signal(engine, confidence=71.06)
    _signal(engine, confidence=87.77)
    _signal(engine, confidence=100.0)

    bands = {row["key"]: row["metrics"]["trades"] for row in _get(client, engine)["by_confidence"]}

    assert bands == {"<60": 1, "70-79": 1, "80+": 2}


def test_no_filled_trade_falls_outside_every_confidence_band(
    client: TestClient, engine
) -> None:
    """A `None` band key means the band list does not cover the scale the
    column actually uses. It must never appear for an ordinary trade."""
    _signal(engine, confidence=82.4)

    keys = [row["key"] for row in _get(client, engine)["by_confidence"]]

    assert None not in keys


def test_risk_review_splits_outcomes_by_verdict(client: TestClient, engine) -> None:
    """ADR-167's comparison - approve versus veto - is the one that decides
    whether the review gets enforced or switched off."""
    _signal(engine, status=SignalStatus.SUCCESSFUL, profit_loss="30", verdict="approve")
    _signal(engine, status=SignalStatus.STOPPED_OUT, profit_loss="-10", verdict="veto")
    _signal(engine, status=SignalStatus.SUCCESSFUL, profit_loss="5", verdict=None)

    rows = {row["key"]: row["metrics"] for row in _get(client, engine)["risk_review"]}

    assert rows["approve"]["wins"] == 1
    assert rows["veto"]["losses"] == 1
    # "We never asked" stays its own group, not merged into approve.
    assert rows[None]["trades"] == 1


def test_replacements_are_counted_and_declared_not_comparable(client: TestClient, engine) -> None:
    """ADR-168: the replaced signal is cancelled and unfilled, so it has no
    outcome, and the signal that replaced it is marked in no column. The
    response says so instead of implying zero."""
    _signal(
        engine,
        status=SignalStatus.CANCELLED,
        triggered_at=None,
        profit_loss=None,
        status_reason=REPLACED_REASON,
    )

    replacements = _get(client, engine)["replacements"]

    assert replacements["signals_replaced"] == 1
    assert replacements["comparable"] is False
    assert "no outcome" in replacements["note"]


# --- Contract ------------------------------------------------------------


def test_epoch_and_points_note_are_always_present(client: TestClient, engine) -> None:
    """A caller must never read a rate without knowing what it excludes or
    what units it is in - including on an empty database."""
    body = _get(client, engine)

    assert body["epoch"].startswith(_EPOCH.date().isoformat())
    assert "price points" in body["points_note"]
    assert "not dollars" in body["points_note"].lower()


def test_points_are_never_labelled_as_currency(client: TestClient, engine) -> None:
    """The field is `total_points`. Never `total_pnl`, never `profit_usd`
    (ADR-174) - one symbol and one lot size is what makes the sum legible
    at all."""
    _signal(engine, profit_loss="10")

    overall = _get(client, engine)["overall"]

    assert "total_points" in overall
    assert not any(key in overall for key in ("total_pnl", "profit_usd", "total_usd"))


# --- Authorization -------------------------------------------------------


def test_performance_rejects_non_admin(client: TestClient, engine) -> None:
    _act_as(
        client,
        _make_user(engine, email="reg@example.com", username="reg", role=UserRole.REGISTERED),
    )

    response = client.get("/api/v1/admin/performance")

    assert response.status_code == 403
    assert response.json()["error"] == "insufficient_role"


def test_performance_rejects_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/v1/admin/performance")

    assert response.status_code == 401


def test_performance_route_exposes_no_non_get_method(client: TestClient) -> None:
    """Read-only by design. Checks the real OpenAPI schema so a future
    accidental POST/PATCH/DELETE under this path fails here."""
    schema = client.get("/api/v1/openapi.json").json()
    paths = {
        path: set(ops)
        for path, ops in schema["paths"].items()
        if path.startswith("/api/v1/admin/performance")
    }

    assert paths == {"/api/v1/admin/performance": {"get"}}

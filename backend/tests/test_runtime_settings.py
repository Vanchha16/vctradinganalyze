"""ADR-178 - strategy and signal settings the super admin changes at runtime.

What must hold, because these values change what the EA trades:
- invalid values, and invalid *combinations*, are refused and change nothing;
- the overlay only touches its own keys, restores the exact `.env` value on
  reset, and never fails the caller when the database cannot be read;
- a disabled strategy is still scored but can never be primary;
- only the super admin can read or change them, and every change is audited.
"""

from collections.abc import Generator
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
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.services import runtime_settings
from app.services.runtime_settings import BY_FIELD, RuntimeSettingError, storage_key
from app.services.strategy import ranking
from app.services.strategy.types import StrategyBreakdown, StrategyName

# --- Parsing and validation ------------------------------------------------


def test_bool_setting_accepts_booleans_and_their_stored_form() -> None:
    spec = BY_FIELD["tight_m5_enabled"]
    assert spec.parse(True) is True
    assert spec.parse("false") is False
    with pytest.raises(RuntimeSettingError):
        spec.parse("yes")


def test_numbers_are_bounded() -> None:
    stop = BY_FIELD["tight_m5_stop_distance"]
    assert stop.parse("7.5") == Decimal("7.5")
    with pytest.raises(RuntimeSettingError, match="at least 1"):
        stop.parse("0")
    with pytest.raises(RuntimeSettingError, match="at most 50"):
        stop.parse("51")
    with pytest.raises(RuntimeSettingError, match="number"):
        stop.parse("abc")
    with pytest.raises(RuntimeSettingError, match="number"):
        stop.parse("NaN")


def test_whole_number_settings_refuse_fractions() -> None:
    with pytest.raises(RuntimeSettingError, match="whole number"):
        BY_FIELD["signal_ttl_hours"].parse("1.5")
    assert BY_FIELD["signal_ttl_hours"].parse(12) == 12


def test_choices_are_restricted() -> None:
    spec = BY_FIELD["ai_risk_review_mode"]
    assert spec.parse("ENFORCE") == "enforce"
    with pytest.raises(RuntimeSettingError):
        spec.parse("sometimes")


def test_disabled_strategies_are_validated_and_kept_in_a_stable_order() -> None:
    spec = BY_FIELD["disabled_strategies"]
    assert spec.parse(["bbma", "breakout"]) == ("breakout", "bbma")
    assert spec.parse("bbma,breakout") == ("breakout", "bbma")
    assert spec.parse([]) == ()
    with pytest.raises(RuntimeSettingError, match="Unknown strategy"):
        spec.parse(["martingale"])


def _current() -> dict[str, object]:
    return {spec.field: getattr(settings, spec.field) for spec in runtime_settings.REGISTRY}


def test_a_target_below_twice_the_stop_is_refused() -> None:
    """The project's minimum risk/reward is 1:2. A tight target below that
    would produce setups the rest of the pipeline treats as sub-minimum."""
    with pytest.raises(RuntimeSettingError, match="at least 2x"):
        runtime_settings.validate_batch({"tight_m5_target_distance": "8"}, _current())


def test_a_stop_and_its_target_can_change_together_in_one_batch() -> None:
    """Raising the stop alone would fail against the old target; the batch
    is validated as a whole, so both move at once."""
    parsed = runtime_settings.validate_batch(
        {"tight_m5_stop_distance": "8", "tight_m5_target_distance": "16"}, _current()
    )
    assert parsed == {
        "tight_m5_stop_distance": Decimal("8"),
        "tight_m5_target_distance": Decimal("16"),
    }


def test_unknown_settings_are_refused() -> None:
    with pytest.raises(RuntimeSettingError, match="Unknown setting"):
        runtime_settings.validate_batch({"openai_api_key": "x"}, _current())


# --- The overlay -----------------------------------------------------------


def test_the_overlay_applies_a_stored_value_and_restores_the_env_value() -> None:
    original = settings.tight_m5_enabled
    runtime_settings.apply_rows({storage_key("tight_m5_enabled"): str(not original).lower()})
    assert settings.tight_m5_enabled is (not original)

    runtime_settings.apply_rows({})
    assert settings.tight_m5_enabled is original


def test_the_overlay_never_touches_a_setting_it_did_not_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no stored rows it must change nothing - including values a test
    (or anything else) set directly."""
    monkeypatch.setattr(settings, "signal_ttl_hours", 5)
    runtime_settings.apply_rows({})
    assert settings.signal_ttl_hours == 5


def test_the_overlay_ignores_keys_outside_its_registry() -> None:
    before = settings.openai_api_key
    runtime_settings.apply_rows({storage_key("openai_api_key"): "stolen"})
    assert settings.openai_api_key == before


def test_a_stored_value_that_no_longer_parses_is_skipped_not_fatal() -> None:
    before = settings.signal_ttl_hours
    runtime_settings.apply_rows({storage_key("signal_ttl_hours"): "banana"})
    assert settings.signal_ttl_hours == before


def test_refresh_is_fail_open() -> None:
    """A settings lookup must never be why a signal task fails."""

    def broken() -> dict[str, str]:
        raise RuntimeError("database down")

    runtime_settings.refresh(force=True, loader=broken)  # must not raise


def test_refresh_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def counting() -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {}

    runtime_settings.refresh(force=True, loader=counting)
    runtime_settings.refresh(loader=counting)
    runtime_settings.refresh(loader=counting)
    assert calls == 1


# --- Disabling a strategy --------------------------------------------------


def _breakdown(total: float) -> StrategyBreakdown:
    """`total` is the capped SUM of the five components, so each gets a
    fifth - putting `total` in every component would cap them all at 100
    and tie every strategy."""
    part = total / 5
    return StrategyBreakdown(
        market_match=part,
        evidence_quality=part,
        confidence=part,
        risk=part,
        historical_performance=part,
    )


def _scores(best: StrategyName) -> dict[StrategyName, StrategyBreakdown]:
    return {s: _breakdown(90.0 if s is best else 60.0) for s in StrategyName}


def test_a_disabled_strategy_is_rejected_with_a_reason_and_never_primary() -> None:
    primary, _, alternatives, rejected = ranking.rank(
        _scores(StrategyName.BBMA), frozenset({StrategyName.BBMA})
    )
    assert primary is not StrategyName.BBMA
    assert StrategyName.BBMA not in {a.strategy for a in alternatives}
    reasons = {r.strategy: r.reason for r in rejected}
    assert reasons[StrategyName.BBMA] == ranking.DISABLED_REASON


def test_with_every_strategy_disabled_there_is_no_primary() -> None:
    primary, _, _, rejected = ranking.rank(_scores(StrategyName.SMC), frozenset(StrategyName))
    assert primary is None
    assert len(rejected) == len(StrategyName)


def test_nothing_disabled_ranks_exactly_as_before() -> None:
    assert ranking.rank(_scores(StrategyName.SMC))[0] is StrategyName.SMC


# --- API: access, changes, audit ------------------------------------------

_TABLES = [User.__table__, SystemSetting.__table__, AuditLog.__table__]


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    return engine


@pytest.fixture
def client(engine) -> Generator[TestClient, None, None]:  # type: ignore[no-untyped-def]
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


def _user(engine, role: UserRole, name: str) -> User:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        user = User(
            email=f"{name}@example.com",
            username=name,
            password_hash=hash_password("Correct-Horse9"),
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _as(client: TestClient, user: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: user


def _audit_rows(engine) -> list[AuditLog]:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        return list(session.query(AuditLog).order_by(AuditLog.created_at).all())


_URL = "/api/v1/admin/runtime-settings"


def test_unauthenticated_is_refused(client: TestClient) -> None:
    assert client.get(_URL).status_code == 401


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.REGISTERED])
def test_only_the_super_admin_may_read_or_change(client: TestClient, engine, role) -> None:  # type: ignore[no-untyped-def]
    """Same boundary as EA tokens (ADR-161): these change what the EA trades."""
    _as(client, _user(engine, role, role.value))
    assert client.get(_URL).status_code == 403
    assert client.put(_URL, json={"changes": {"tight_m5_enabled": True}}).status_code == 403


def test_the_list_shows_every_setting_at_its_env_default(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _as(client, _user(engine, UserRole.SUPER_ADMIN, "owner"))
    body = client.get(_URL).json()

    assert body["propagation_seconds"] == 30
    assert {i["key"] for i in body["items"]} == set(BY_FIELD)
    for item in body["items"]:
        assert item["overridden"] is False
        assert item["value"] == item["default"]


def test_a_change_is_stored_applied_and_audited(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    owner = _user(engine, UserRole.SUPER_ADMIN, "owner")
    _as(client, owner)
    original = settings.tight_m5_enabled

    response = client.put(_URL, json={"changes": {"tight_m5_enabled": not original}})

    assert response.status_code == 200, response.text
    item = next(i for i in response.json()["items"] if i["key"] == "tight_m5_enabled")
    assert item["value"] is (not original) and item["overridden"] is True
    # This process takes the change at once; others within 30 seconds.
    assert settings.tight_m5_enabled is (not original)

    [audit] = _audit_rows(engine)
    assert audit.user_id == owner.id
    assert audit.action == "runtime_setting_changed"
    assert audit.context == {
        "setting": "tight_m5_enabled",
        "old": str(original).lower(),
        "new": str(not original).lower(),
    }


def test_null_resets_to_the_env_value_and_is_audited(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _as(client, _user(engine, UserRole.SUPER_ADMIN, "owner"))
    original = settings.signal_ttl_hours
    client.put(_URL, json={"changes": {"signal_ttl_hours": original + 1}})
    assert settings.signal_ttl_hours == original + 1

    response = client.put(_URL, json={"changes": {"signal_ttl_hours": None}})

    assert response.status_code == 200
    item = next(i for i in response.json()["items"] if i["key"] == "signal_ttl_hours")
    assert item["overridden"] is False and item["value"] == original
    assert settings.signal_ttl_hours == original
    assert [a.action for a in _audit_rows(engine)] == [
        "runtime_setting_changed",
        "runtime_setting_reset",
    ]


def test_an_invalid_batch_changes_nothing(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    """One bad value in a batch rejects the whole batch - the valid half
    must not be written either."""
    _as(client, _user(engine, UserRole.SUPER_ADMIN, "owner"))
    before = settings.signal_ttl_hours

    response = client.put(
        _URL, json={"changes": {"signal_ttl_hours": before + 1, "ai_risk_review_mode": "maybe"}}
    )

    assert response.status_code == 422
    assert settings.signal_ttl_hours == before
    assert _audit_rows(engine) == []
    with Session(engine) as session:
        assert session.query(SystemSetting).count() == 0


def test_a_change_to_the_same_value_is_not_audited(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _as(client, _user(engine, UserRole.SUPER_ADMIN, "owner"))
    client.put(_URL, json={"changes": {"signal_ttl_hours": settings.signal_ttl_hours}})
    assert _audit_rows(engine) == []


def test_disabling_strategies_through_the_api_reaches_the_engine(
    client: TestClient, engine
) -> None:  # type: ignore[no-untyped-def]
    from app.services.strategy_engine import _disabled_strategies

    _as(client, _user(engine, UserRole.SUPER_ADMIN, "owner"))
    response = client.put(_URL, json={"changes": {"disabled_strategies": ["bbma", "breakout"]}})

    assert response.status_code == 200
    assert _disabled_strategies() == frozenset({StrategyName.BBMA, StrategyName.BREAKOUT})


def test_the_route_exposes_only_get_and_put(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()
    assert set(schema["paths"][_URL]) == {"get", "put"}

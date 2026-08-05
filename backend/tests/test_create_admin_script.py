"""Phase 8E (docs/59 §9/§12, ADR-123) - backend/scripts/create_admin.py."""

import builtins
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import scripts.create_admin as create_admin
from app.core.security import verify_password
from app.database.base import Base
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.models.user_session import UserSession

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    AuditLog.__table__,
]


@pytest.fixture
def session_factory(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=_TABLES)
    session = Session(engine)
    monkeypatch.setattr(create_admin, "SessionLocal", lambda: session)
    return session


def _feed(monkeypatch: pytest.MonkeyPatch, inputs: list[str], passwords: list[str]) -> None:
    input_iter: Iterator[str] = iter(inputs)
    password_iter: Iterator[str] = iter(passwords)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(input_iter))
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": next(password_iter))


def test_create_admin_creates_first_super_admin(
    session_factory: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(
        monkeypatch,
        inputs=["admin@example.com", "superadmin"],
        passwords=["Correct-Horse9", "Correct-Horse9"],
    )

    exit_code = create_admin.main()

    assert exit_code == 0
    user = session_factory.execute(select(User)).scalar_one()
    assert user.role == UserRole.SUPER_ADMIN
    assert user.must_change_password is False
    assert user.created_by_admin_id is None
    assert verify_password("Correct-Horse9", user.password_hash)


def test_create_admin_refuses_a_second_bootstrap(
    session_factory: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(
        monkeypatch,
        inputs=["admin@example.com", "superadmin"],
        passwords=["Correct-Horse9", "Correct-Horse9"],
    )
    assert create_admin.main() == 0

    # A second attempt should be refused before ever prompting again -
    # feed inputs that would raise StopIteration if actually consumed.
    _feed(monkeypatch, inputs=[], passwords=[])

    exit_code = create_admin.main()

    assert exit_code == 1
    assert session_factory.execute(select(User)).scalars().all().__len__() == 1


def test_create_admin_rejects_mismatched_password_confirmation_then_succeeds(
    session_factory: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(
        monkeypatch,
        inputs=["admin@example.com", "superadmin"],
        passwords=["Correct-Horse9", "wrong-confirm", "Correct-Horse9", "Correct-Horse9"],
    )

    exit_code = create_admin.main()

    assert exit_code == 0
    user = session_factory.execute(select(User)).scalar_one()
    assert verify_password("Correct-Horse9", user.password_hash)


def test_create_admin_rejects_weak_password(
    session_factory: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(
        monkeypatch,
        inputs=["admin@example.com", "superadmin"],
        passwords=["short", "short"],
    )

    exit_code = create_admin.main()

    assert exit_code == 1
    assert session_factory.execute(select(User)).scalars().all() == []

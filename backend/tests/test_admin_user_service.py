import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.database.base import Base
from app.exceptions import (
    ConflictException,
    InsufficientRoleException,
    LastSuperAdminException,
    ResourceNotFoundException,
)
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.admin_user_service import AdminUserService
from app.services.user_service import UserService

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    AuditLog.__table__,
]

_PASSWORD = "Correct-Horse9"


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


@pytest.fixture
def service(session: Session) -> AdminUserService:
    user_repository = UserRepository(session)
    return AdminUserService(
        user_repository,
        UserSessionRepository(session),
        AuditLogRepository(session),
        UserService(user_repository),
    )


def _make_user(session: Session, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": "user@example.com",
        "username": "user",
        "password_hash": hash_password(_PASSWORD),
        "role": UserRole.REGISTERED,
    }
    defaults.update(overrides)
    user = User(**defaults)
    session.add(user)
    session.commit()
    return user


def _last_audit(session: Session) -> AuditLog:
    return session.execute(select(AuditLog).order_by(AuditLog.created_at.desc())).scalars().first()


# --- create_user -------------------------------------------------------


def test_create_user_generates_temp_password_when_none_supplied(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    user, temp_password = service.create_user(
        admin,
        email="new@example.com",
        username="newuser",
        full_name=None,
        role=UserRole.REGISTERED,
        password=None,
    )

    assert temp_password is not None
    assert verify_password(temp_password, user.password_hash)


def test_create_user_sets_must_change_password_even_with_explicit_password(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    user, temp_password = service.create_user(
        admin,
        email="new@example.com",
        username="newuser",
        full_name=None,
        role=UserRole.REGISTERED,
        password="Explicit-Pass9",
    )

    assert temp_password is None
    assert user.must_change_password is True


def test_create_user_records_created_by_admin_id(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    user, _ = service.create_user(
        admin,
        email="new@example.com",
        username="newuser",
        full_name=None,
        role=UserRole.REGISTERED,
        password=None,
    )

    assert user.created_by_admin_id == admin.id


def test_create_user_writes_audit_log(service: AdminUserService, session: Session) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    user, _ = service.create_user(
        admin,
        email="new@example.com",
        username="newuser",
        full_name=None,
        role=UserRole.REGISTERED,
        password=None,
    )

    entry = _last_audit(session)
    assert entry.action == "admin_user_created"
    assert entry.user_id == admin.id
    assert entry.resource_id == user.id
    assert entry.resource == "user"


def test_create_user_admin_cannot_create_admin_tier_account(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    with pytest.raises(InsufficientRoleException):
        service.create_user(
            admin,
            email="new@example.com",
            username="newuser",
            full_name=None,
            role=UserRole.ADMIN,
            password=None,
        )


def test_create_user_super_admin_can_create_admin_tier_account(
    service: AdminUserService, session: Session
) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )

    user, _ = service.create_user(
        super_admin,
        email="new-admin@example.com",
        username="newadmin",
        full_name=None,
        role=UserRole.ADMIN,
        password=None,
    )

    assert user.role == UserRole.ADMIN


# --- list_users ----------------------------------------------------------


def test_list_users_filters_by_role_and_search(service: AdminUserService, session: Session) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_user(session, email="alice@example.com", username="alice", role=UserRole.REGISTERED)
    _make_user(session, email="bob@example.com", username="bob", role=UserRole.PREMIUM)

    items, total = service.list_users(admin, role=UserRole.PREMIUM)
    assert total == 1
    assert items[0].username == "bob"

    items, total = service.list_users(admin, search="alice")
    assert total == 1
    assert items[0].username == "alice"


def test_list_users_pagination(service: AdminUserService, session: Session) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    for i in range(5):
        _make_user(session, email=f"u{i}@example.com", username=f"u{i}")

    items, total = service.list_users(admin, page=1, limit=2)
    assert total == 6  # 5 + admin
    assert len(items) == 2


def test_list_users_excludes_deleted_by_default(
    service: AdminUserService, session: Session
) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    target = _make_user(session, email="gone@example.com", username="gone")
    service.delete_user(super_admin, target.id)

    items, total = service.list_users(super_admin)
    assert target.id not in {u.id for u in items}
    assert total == 1  # only super_admin


def test_list_users_include_deleted_requires_super_admin(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    with pytest.raises(InsufficientRoleException):
        service.list_users(admin, include_deleted=True)


def test_list_users_include_deleted_allowed_for_super_admin(
    service: AdminUserService, session: Session
) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    target = _make_user(session, email="gone@example.com", username="gone")
    service.delete_user(super_admin, target.id)

    items, total = service.list_users(super_admin, include_deleted=True)
    assert target.id in {u.id for u in items}
    assert total == 2


# --- get_user_detail -----------------------------------------------------


def test_get_user_detail_returns_active_session_count(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(session, email="target@example.com", username="target")
    session.add(
        UserSession(
            user_id=target.id,
            refresh_token_hash="hash1",
            expires_at=target.created_at,
        )
    )
    session.commit()

    _, active_session_count = service.get_user_detail(admin, target.id)
    assert active_session_count == 1


def test_get_user_detail_raises_not_found_for_unknown_user(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    with pytest.raises(ResourceNotFoundException):
        service.get_user_detail(admin, uuid.uuid4())


# --- update_user -----------------------------------------------------------


def test_update_user_changes_fields_and_audits(service: AdminUserService, session: Session) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(session, email="target@example.com", username="target")

    updated = service.update_user(admin, target.id, full_name="New Name")

    assert updated.full_name == "New Name"
    entry = _last_audit(session)
    assert entry.action == "admin_user_updated"
    assert entry.context["new"]["full_name"] == "New Name"


def test_update_user_rejects_duplicate_username(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    _make_user(session, email="taken@example.com", username="taken")
    target = _make_user(session, email="target@example.com", username="target")

    with pytest.raises(ConflictException):
        service.update_user(admin, target.id, username="taken")


def test_update_user_admin_cannot_act_on_admin_target(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    other_admin = _make_user(
        session, email="other-admin@example.com", username="otheradmin", role=UserRole.ADMIN
    )

    with pytest.raises(InsufficientRoleException):
        service.update_user(admin, other_admin.id, full_name="Hacked")


def test_update_user_super_admin_can_act_on_admin_target(
    service: AdminUserService, session: Session
) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    admin_target = _make_user(
        session, email="admin-target@example.com", username="admintarget", role=UserRole.ADMIN
    )

    updated = service.update_user(super_admin, admin_target.id, full_name="Renamed")
    assert updated.full_name == "Renamed"


# --- set_status -----------------------------------------------------------


def test_set_status_disable_revokes_sessions_and_audits(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(session, email="target@example.com", username="target")
    session.add(
        UserSession(user_id=target.id, refresh_token_hash="hash1", expires_at=target.created_at)
    )
    session.commit()

    updated = service.set_status(admin, target.id, is_active=False)

    assert updated.is_active is False
    remaining = (
        session.execute(select(UserSession).where(UserSession.user_id == target.id)).scalars().all()
    )
    assert remaining == []
    entry = _last_audit(session)
    assert entry.action == "admin_user_disabled"


def test_set_status_activate_writes_activated_action(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(session, email="target@example.com", username="target", is_active=False)

    service.set_status(admin, target.id, is_active=True)

    entry = _last_audit(session)
    assert entry.action == "admin_user_activated"


def test_set_status_blocks_suspending_last_active_super_admin(
    service: AdminUserService, session: Session
) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )

    with pytest.raises(LastSuperAdminException):
        service.set_status(super_admin, super_admin.id, is_active=False)


def test_set_status_allows_suspending_super_admin_when_another_is_active(
    service: AdminUserService, session: Session
) -> None:
    super_admin_1 = _make_user(
        session, email="super1@example.com", username="super1", role=UserRole.SUPER_ADMIN
    )
    super_admin_2 = _make_user(
        session, email="super2@example.com", username="super2", role=UserRole.SUPER_ADMIN
    )

    updated = service.set_status(super_admin_1, super_admin_2.id, is_active=False)
    assert updated.is_active is False


# --- change_role -----------------------------------------------------------


def test_change_role_updates_and_audits(service: AdminUserService, session: Session) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    target = _make_user(session, email="target@example.com", username="target")

    updated = service.change_role(super_admin, target.id, new_role=UserRole.PREMIUM)

    assert updated.role == UserRole.PREMIUM
    entry = _last_audit(session)
    assert entry.action == "admin_role_changed"
    assert entry.context["old"]["role"] == "registered"
    assert entry.context["new"]["role"] == "premium"


def test_change_role_blocks_demoting_last_super_admin(
    service: AdminUserService, session: Session
) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )

    with pytest.raises(LastSuperAdminException):
        service.change_role(super_admin, super_admin.id, new_role=UserRole.ADMIN)


def test_change_role_allows_demoting_when_another_super_admin_exists(
    service: AdminUserService, session: Session
) -> None:
    super_admin_1 = _make_user(
        session, email="super1@example.com", username="super1", role=UserRole.SUPER_ADMIN
    )
    super_admin_2 = _make_user(
        session, email="super2@example.com", username="super2", role=UserRole.SUPER_ADMIN
    )

    updated = service.change_role(super_admin_1, super_admin_2.id, new_role=UserRole.ADMIN)
    assert updated.role == UserRole.ADMIN


# --- reset_password --------------------------------------------------------


def test_reset_password_sets_must_change_password_and_revokes_sessions(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(session, email="target@example.com", username="target")
    session.add(
        UserSession(user_id=target.id, refresh_token_hash="hash1", expires_at=target.created_at)
    )
    session.commit()

    temp_password = service.reset_password(admin, target.id)

    session.refresh(target)
    assert verify_password(temp_password, target.password_hash)
    assert target.must_change_password is True
    remaining = (
        session.execute(select(UserSession).where(UserSession.user_id == target.id)).scalars().all()
    )
    assert remaining == []


def test_reset_password_does_not_log_plaintext_password(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(session, email="target@example.com", username="target")

    temp_password = service.reset_password(admin, target.id)

    entry = _last_audit(session)
    assert entry.action == "admin_password_reset"
    assert entry.context is None
    assert temp_password  # sanity: a real password was actually generated


# --- delete_user -----------------------------------------------------------


def test_delete_user_soft_deletes_and_audits(service: AdminUserService, session: Session) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    target = _make_user(session, email="target@example.com", username="target")

    service.delete_user(admin, target.id)

    session.refresh(target)
    assert target.deleted_at is not None
    assert target.is_active is False
    entry = _last_audit(session)
    assert entry.action == "admin_user_deleted"


def test_delete_user_blocks_self_delete(service: AdminUserService, session: Session) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)

    with pytest.raises(ConflictException):
        service.delete_user(admin, admin.id)


def test_delete_user_blocks_when_actor_is_the_only_active_super_admin(
    service: AdminUserService, session: Session
) -> None:
    """Self-delete is already unconditionally blocked (`ConflictException`,
    tested above), so the last-super-admin guard's reachable case is a
    *different* target: an already-inactive super admin, deleted by the
    sole remaining active one."""
    actor = _make_user(
        session, email="super1@example.com", username="super1", role=UserRole.SUPER_ADMIN
    )
    target = _make_user(
        session,
        email="super2@example.com",
        username="super2",
        role=UserRole.SUPER_ADMIN,
        is_active=False,
    )

    with pytest.raises(LastSuperAdminException):
        service.delete_user(actor, target.id)


def test_delete_user_allows_deleting_super_admin_when_another_is_active(
    service: AdminUserService, session: Session
) -> None:
    actor = _make_user(
        session, email="super1@example.com", username="super1", role=UserRole.SUPER_ADMIN
    )
    target = _make_user(
        session, email="super2@example.com", username="super2", role=UserRole.SUPER_ADMIN
    )

    service.delete_user(actor, target.id)

    session.refresh(target)
    assert target.deleted_at is not None


def test_delete_user_admin_cannot_delete_admin_target(
    service: AdminUserService, session: Session
) -> None:
    admin = _make_user(session, email="admin@example.com", username="admin", role=UserRole.ADMIN)
    other_admin = _make_user(
        session, email="other-admin@example.com", username="otheradmin", role=UserRole.ADMIN
    )

    with pytest.raises(InsufficientRoleException):
        service.delete_user(admin, other_admin.id)


def test_delete_user_raises_not_found_for_already_deleted_user(
    service: AdminUserService, session: Session
) -> None:
    super_admin = _make_user(
        session, email="super@example.com", username="super", role=UserRole.SUPER_ADMIN
    )
    target = _make_user(session, email="target@example.com", username="target")
    service.delete_user(super_admin, target.id)

    with pytest.raises(ResourceNotFoundException):
        service.delete_user(super_admin, target.id)

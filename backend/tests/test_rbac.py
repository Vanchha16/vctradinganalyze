"""Phase 8B - docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md §6 / §11."""

import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    require_admin,
    require_permission,
    require_role,
    require_super_admin,
)
from app.exceptions import InsufficientRoleException, register_exception_handlers
from app.models.enums import UserRole
from app.models.user import User


def _make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        username="user",
        password_hash=hash_password("Correct-Horse9"),
        role=role,
    )


# --- require_role -----------------------------------------------------------


def test_require_role_allows_a_listed_role() -> None:
    check = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    user = _make_user(UserRole.ADMIN)

    assert check(current_user=user) is user


def test_require_role_rejects_an_unlisted_role() -> None:
    check = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    user = _make_user(UserRole.REGISTERED)

    with pytest.raises(InsufficientRoleException):
        check(current_user=user)


def test_require_role_with_a_single_role() -> None:
    check = require_role(UserRole.SUPER_ADMIN)

    assert check(current_user=_make_user(UserRole.SUPER_ADMIN)) is not None
    with pytest.raises(InsufficientRoleException):
        check(current_user=_make_user(UserRole.ADMIN))


# --- require_admin / require_super_admin ------------------------------------


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.SUPER_ADMIN])
def test_require_admin_allows_admin_and_super_admin(role: UserRole) -> None:
    user = _make_user(role)

    assert require_admin(current_user=user) is user


@pytest.mark.parametrize(
    "role",
    [UserRole.GUEST, UserRole.REGISTERED, UserRole.PREMIUM, UserRole.MODERATOR, UserRole.SUPPORT],
)
def test_require_admin_rejects_every_non_admin_role(role: UserRole) -> None:
    with pytest.raises(InsufficientRoleException):
        require_admin(current_user=_make_user(role))


def test_require_super_admin_allows_only_super_admin() -> None:
    assert require_super_admin(current_user=_make_user(UserRole.SUPER_ADMIN)) is not None


def test_require_super_admin_rejects_plain_admin() -> None:
    """The core vertical-access boundary (ADR-121) - a regular Admin must
    not pass a Super-Admin-only check, e.g. role changes."""
    with pytest.raises(InsufficientRoleException):
        require_super_admin(current_user=_make_user(UserRole.ADMIN))


# --- Permission / ROLE_PERMISSIONS (ADR-122) --------------------------------


def test_role_permissions_grants_admin_read_and_write_only() -> None:
    assert ROLE_PERMISSIONS[UserRole.ADMIN] == frozenset(
        {Permission.USERS_READ, Permission.USERS_WRITE}
    )


def test_role_permissions_grants_super_admin_every_permission() -> None:
    assert ROLE_PERMISSIONS[UserRole.SUPER_ADMIN] == frozenset(Permission.__members__.values())


def test_require_permission_allows_a_granted_permission() -> None:
    check = require_permission(Permission.USERS_WRITE)
    user = _make_user(UserRole.ADMIN)

    assert check(current_user=user) is user


def test_require_permission_rejects_an_ungranted_permission() -> None:
    """Admin has USERS_WRITE but not ROLES_MANAGE - only Super Admin does."""
    check = require_permission(Permission.ROLES_MANAGE)

    with pytest.raises(InsufficientRoleException):
        check(current_user=_make_user(UserRole.ADMIN))


def test_require_permission_rejects_roles_with_no_entry_in_the_mapping() -> None:
    """Registered/Premium/Moderator/Support have no `ROLE_PERMISSIONS` entry
    at all - `.get(..., frozenset())` must not raise a `KeyError`."""
    check = require_permission(Permission.USERS_READ)

    with pytest.raises(InsufficientRoleException):
        check(current_user=_make_user(UserRole.REGISTERED))


# --- End-to-end through the real exception handler --------------------------


@pytest.fixture
def rbac_test_client() -> TestClient:
    """A throwaway app proving `require_admin` composes with the real
    `get_current_user` and that `InsufficientRoleException` is mapped to a
    `403` by the project's actual exception handler - not just that the
    Python function raises."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/admin-only")
    def _admin_only(user: User = Depends(require_admin)) -> dict[str, str]:  # noqa: B008
        return {"email": user.email}

    return TestClient(app)


def test_admin_only_route_allows_admin(rbac_test_client: TestClient) -> None:
    rbac_test_client.app.dependency_overrides[get_current_user] = lambda: _make_user(UserRole.ADMIN)

    response = rbac_test_client.get("/admin-only")

    assert response.status_code == 200


def test_admin_only_route_rejects_registered_user_with_403(rbac_test_client: TestClient) -> None:
    rbac_test_client.app.dependency_overrides[get_current_user] = lambda: _make_user(
        UserRole.REGISTERED
    )

    response = rbac_test_client.get("/admin-only")

    assert response.status_code == 403
    assert response.json()["error"] == "insufficient_role"

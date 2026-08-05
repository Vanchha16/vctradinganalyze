"""Role/permission enforcement (Phase 8B, docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md §6).

`get_current_user` (Phase 2C) remains authentication-only by design - it
resolves a bearer token to a `User` and nothing more. Everything in this
module is purely additive on top of it: it composes `get_current_user` via
`Depends()`, the same pattern every other dependency in this project already
uses (e.g. `get_authentication_service` composing `get_db`), and does not
modify it.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Annotated

from fastapi import Depends

from app.dependencies.auth import get_current_user
from app.exceptions import InsufficientRoleException
from app.models.enums import UserRole
from app.models.user import User


class Permission(StrEnum):
    """Granular capabilities, mapped to roles via `ROLE_PERMISSIONS` below.

    This is a plain in-code seam (ADR-122), not a database table - ADR-115
    already deferred the full `roles`/`permissions`/`role_permissions`
    schema (docs/23 §12-14) since no route needs finer-than-role granularity
    yet. If that ever changes, `ROLE_PERMISSIONS` is the one place that
    moves from a hardcoded dict to a DB-backed lookup; every
    `Depends(require_permission(...))` call site is unaffected.
    """

    USERS_READ = "users.read"
    USERS_WRITE = "users.write"
    USERS_DELETE = "users.delete"
    ROLES_MANAGE = "roles.manage"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset({Permission.USERS_READ, Permission.USERS_WRITE}),
    UserRole.SUPER_ADMIN: frozenset(Permission.__members__.values()),
}
"""Every role not listed here (guest/registered/premium/moderator/support)
has no permissions - only Admin and Super Admin have any `/admin/*` access
in this phase (docs/59 §11 - no documented endpoint maps to
Moderator/Support's docs/23 §13 permissions yet)."""


def require_role(*roles: UserRole) -> Callable[..., User]:
    """Build a dependency that allows only the given roles.

    Usage: `Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))`.
    """

    def _check_role(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise InsufficientRoleException()
        return current_user

    return _check_role


def require_permission(permission: Permission) -> Callable[..., User]:
    """Build a dependency that allows only roles granted `permission` via `ROLE_PERMISSIONS`."""

    def _check_permission(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if permission not in ROLE_PERMISSIONS.get(current_user.role, frozenset()):
            raise InsufficientRoleException()
        return current_user

    return _check_permission


require_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_role(UserRole.SUPER_ADMIN)

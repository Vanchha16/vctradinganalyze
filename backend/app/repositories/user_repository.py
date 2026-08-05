import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select

from app.models.enums import UserRole
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Returns the row regardless of `deleted_at` - callers (e.g.
        `AdminUserService`) decide soft-delete visibility themselves, since
        an admin viewing a specific deleted user's history is a different
        need than a general listing (docs/59 §6.2)."""
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        query = self._filter_by(self._query(), email=email)
        return self.session.execute(query).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        query = self._filter_by(self._query(), username=username)
        return self.session.execute(query).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def list_paginated(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> Sequence[User]:
        query = self._apply_admin_filters(
            self._query(),
            search=search,
            role=role,
            is_active=is_active,
            include_deleted=include_deleted,
        )
        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(
        self,
        *,
        search: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        query = self._apply_admin_filters(
            self._query(),
            search=search,
            role=role,
            is_active=is_active,
            include_deleted=include_deleted,
        )
        return self._count(query)

    def _apply_admin_filters(
        self,
        query: Select[tuple[User]],
        *,
        search: str | None,
        role: UserRole | None,
        is_active: bool | None,
        include_deleted: bool,
    ) -> Select[tuple[User]]:
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.email.ilike(pattern),
                    User.username.ilike(pattern),
                    User.full_name.ilike(pattern),
                )
            )
        if role is not None:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        return query

    def soft_delete(self, user: User) -> None:
        """Sets `deleted_at` and `is_active=False` (docs/59 §4/ADR-120) -
        never removes the row, never cascades. `is_active=False` is
        additive belt-and-braces: any code path that only checks
        `is_active` (not `deleted_at`) still treats the account as
        unusable."""
        user.deleted_at = datetime.now(UTC)
        user.is_active = False

    def count_by_role(self, role: UserRole, *, active_only: bool = False) -> int:
        """Excludes soft-deleted rows always - used for the "last super
        admin" guard (docs/59 §6.2/§11), where a deleted super-admin row
        must not count as a still-available one."""
        query = (
            select(func.count())
            .select_from(User)
            .where(User.role == role, User.deleted_at.is_(None))
        )
        if active_only:
            query = query.where(User.is_active.is_(True))
        return self.session.execute(query).scalar_one()

import uuid
from typing import Any

import structlog

from app.core.security import generate_temporary_password, hash_password
from app.exceptions import (
    ConflictException,
    InsufficientRoleException,
    LastSuperAdminException,
    ResourceNotFoundException,
)
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.user_service import UserService

logger = structlog.get_logger(__name__)

_ADMIN_TIER_ROLES = (UserRole.ADMIN, UserRole.SUPER_ADMIN)


class AdminUserService:
    """Business rules for admin-driven user management (Phase 8C,
    docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md §3.3/§6.2/§11).

    Mirrors `AuthenticationService`'s shape exactly: constructor-injected
    repositories, one public method per use case, private `_audit`/`_commit`
    helpers. `create_user` delegates to `UserService.register_user`
    (extended additively for this phase) rather than duplicating
    validation/uniqueness logic, per ADR-119.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        user_session_repository: UserSessionRepository,
        audit_log_repository: AuditLogRepository,
        user_service: UserService,
    ) -> None:
        self._user_repository = user_repository
        self._user_session_repository = user_session_repository
        self._audit_log_repository = audit_log_repository
        self._user_service = user_service

    # --- Reads ---------------------------------------------------------

    def list_users(
        self,
        actor: User,
        *,
        search: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        if include_deleted and actor.role != UserRole.SUPER_ADMIN:
            raise InsufficientRoleException("Only a super admin can list deleted accounts.")

        offset = (page - 1) * limit
        items = self._user_repository.list_paginated(
            offset=offset,
            limit=limit,
            search=search,
            role=role,
            is_active=is_active,
            include_deleted=include_deleted,
        )
        total = self._user_repository.count_filtered(
            search=search, role=role, is_active=is_active, include_deleted=include_deleted
        )
        return list(items), total

    def get_user_detail(self, actor: User, target_id: uuid.UUID) -> tuple[User, int]:
        target = self._resolve_target(target_id)
        self._assert_can_view(actor, target)
        active_session_count = self._user_session_repository.count_for_user(target.id)
        return target, active_session_count

    # --- Mutations -------------------------------------------------------

    def create_user(
        self,
        actor: User,
        *,
        email: str,
        username: str,
        full_name: str | None,
        role: UserRole,
        password: str | None,
        ip_address: str | None = None,
    ) -> tuple[User, str | None]:
        if role in _ADMIN_TIER_ROLES and actor.role != UserRole.SUPER_ADMIN:
            raise InsufficientRoleException("Only a super admin can create an admin-tier account.")

        temporary_password = None
        if password is None:
            temporary_password = generate_temporary_password()
            password = temporary_password

        user = self._user_service.register_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            role=role,
            must_change_password=True,
            created_by_admin_id=actor.id,
        )

        self._audit(
            actor.id,
            action="admin_user_created",
            resource_id=user.id,
            ip_address=ip_address,
            context={"new": {"email": email, "username": username, "role": role.value}},
        )
        self._commit()
        logger.info("admin.user_created", actor_id=str(actor.id), target_id=str(user.id))
        return user, temporary_password

    def update_user(
        self,
        actor: User,
        target_id: uuid.UUID,
        *,
        full_name: str | None = None,
        username: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
    ) -> User:
        target = self._resolve_target(target_id)
        self._assert_can_act_on(actor, target)

        old: dict[str, Any] = {}
        new: dict[str, Any] = {}

        if username is not None and username != target.username:
            existing = self._user_repository.get_by_username(username)
            if existing is not None and existing.id != target.id:
                raise ConflictException("Username is already taken.")
            old["username"], new["username"] = target.username, username
            target.username = username

        if email is not None and email != target.email:
            existing_email = self._user_repository.get_by_email(email)
            if existing_email is not None and existing_email.id != target.id:
                raise ConflictException("Email is already registered.")
            old["email"], new["email"] = target.email, email
            target.email = email

        if full_name is not None and full_name != target.full_name:
            old["full_name"], new["full_name"] = target.full_name, full_name
            target.full_name = full_name

        if new:
            self._audit(
                actor.id,
                action="admin_user_updated",
                resource_id=target.id,
                ip_address=ip_address,
                context={"old": old, "new": new},
            )
            self._commit()
            logger.info("admin.user_updated", actor_id=str(actor.id), target_id=str(target.id))
        return target

    def set_status(
        self,
        actor: User,
        target_id: uuid.UUID,
        *,
        is_active: bool,
        ip_address: str | None = None,
    ) -> User:
        target = self._resolve_target(target_id)
        self._assert_can_act_on(actor, target)

        if not is_active and target.role == UserRole.SUPER_ADMIN:
            self._assert_not_last_active_super_admin(target)

        old_status = target.is_active
        target.is_active = is_active
        if not is_active:
            self._user_session_repository.delete_for_user(target.id)

        self._audit(
            actor.id,
            action="admin_user_disabled" if not is_active else "admin_user_activated",
            resource_id=target.id,
            ip_address=ip_address,
            context={"old": {"is_active": old_status}, "new": {"is_active": is_active}},
        )
        self._commit()
        logger.info(
            "admin.user_status_changed",
            actor_id=str(actor.id),
            target_id=str(target.id),
            is_active=is_active,
        )
        return target

    def change_role(
        self,
        actor: User,
        target_id: uuid.UUID,
        *,
        new_role: UserRole,
        ip_address: str | None = None,
    ) -> User:
        """`require_super_admin` at the route level already restricts who
        can call this at all - the last-super-admin guard here additionally
        blocks a super admin from demoting the only remaining one, self or
        otherwise (ADR-121)."""
        target = self._resolve_target(target_id)

        if target.role == UserRole.SUPER_ADMIN and new_role != UserRole.SUPER_ADMIN:
            self._assert_not_last_active_super_admin(target)

        old_role = target.role
        target.role = new_role

        self._audit(
            actor.id,
            action="admin_role_changed",
            resource_id=target.id,
            ip_address=ip_address,
            context={"old": {"role": old_role.value}, "new": {"role": new_role.value}},
        )
        self._commit()
        logger.info(
            "admin.role_changed",
            actor_id=str(actor.id),
            target_id=str(target.id),
            old_role=old_role.value,
            new_role=new_role.value,
        )
        return target

    def reset_password(
        self, actor: User, target_id: uuid.UUID, *, ip_address: str | None = None
    ) -> str:
        target = self._resolve_target(target_id)
        self._assert_can_act_on(actor, target)

        temporary_password = generate_temporary_password()
        target.password_hash = hash_password(temporary_password)
        target.must_change_password = True
        self._user_session_repository.delete_for_user(target.id)

        # Never write the plaintext password into the audit context (docs/59 §11).
        self._audit(
            actor.id, action="admin_password_reset", resource_id=target.id, ip_address=ip_address
        )
        self._commit()
        logger.info("admin.password_reset", actor_id=str(actor.id), target_id=str(target.id))
        return temporary_password

    def delete_user(
        self, actor: User, target_id: uuid.UUID, *, ip_address: str | None = None
    ) -> None:
        if target_id == actor.id:
            raise ConflictException("You cannot delete your own account.")

        target = self._resolve_target(target_id)
        self._assert_can_act_on(actor, target)

        if target.role == UserRole.SUPER_ADMIN:
            self._assert_not_last_active_super_admin(target)

        self._user_repository.soft_delete(target)
        self._user_session_repository.delete_for_user(target.id)

        self._audit(
            actor.id, action="admin_user_deleted", resource_id=target.id, ip_address=ip_address
        )
        self._commit()
        logger.info("admin.user_deleted", actor_id=str(actor.id), target_id=str(target.id))

    # --- Internal helpers --------------------------------------------------

    def _resolve_target(self, target_id: uuid.UUID) -> User:
        target = self._user_repository.get_by_id(target_id)
        if target is None or target.deleted_at is not None:
            raise ResourceNotFoundException("User not found.")
        return target

    def _assert_can_view(self, actor: User, target: User) -> None:
        self._assert_can_act_on(actor, target)

    def _assert_can_act_on(self, actor: User, target: User) -> None:
        """Vertical-access guard (ADR-121, docs/59 §11) - a plain Admin may
        act on any non-admin-tier target, but never on another Admin or a
        Super Admin. Only a Super Admin may act on admin-tier targets."""
        if target.role in _ADMIN_TIER_ROLES and actor.role != UserRole.SUPER_ADMIN:
            raise InsufficientRoleException("Only a super admin can act on an admin-tier account.")

    def _assert_not_last_active_super_admin(self, target: User) -> None:
        active_super_admins = self._user_repository.count_by_role(
            UserRole.SUPER_ADMIN, active_only=True
        )
        if active_super_admins <= 1:
            raise LastSuperAdminException()

    def _audit(
        self,
        actor_id: uuid.UUID,
        *,
        action: str,
        resource_id: uuid.UUID,
        ip_address: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLog(
                user_id=actor_id,
                action=action,
                resource="user",
                resource_id=resource_id,
                ip_address=ip_address,
                context=context,
            )
        )

    def _commit(self) -> None:
        self._user_repository.commit()

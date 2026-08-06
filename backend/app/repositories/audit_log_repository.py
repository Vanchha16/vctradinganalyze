import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> Sequence[AuditLog]:
        query = self._filter_by(self._query(), user_id=user_id)
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def create(self, log: AuditLog) -> AuditLog:
        self.session.add(log)
        self.session.flush()
        return log

    def list_admin(
        self,
        *,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[AuditLog]:
        """Phase 8F (docs/59 §11, ADR-129) - admin-wide listing, newest
        first. Every filter is optional and combinable, mirrors
        `UserRepository.list_paginated`'s shape."""
        query = self._apply_admin_filters(
            self._query(),
            user_id=user_id,
            action=action,
            resource=resource,
            created_from=created_from,
            created_to=created_to,
        )
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_admin(
        self,
        *,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> int:
        query = self._apply_admin_filters(
            self._query(),
            user_id=user_id,
            action=action,
            resource=resource,
            created_from=created_from,
            created_to=created_to,
        )
        return self._count(query)

    def _apply_admin_filters(
        self,
        query: Select[tuple[AuditLog]],
        *,
        user_id: uuid.UUID | None,
        action: str | None,
        resource: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> Select[tuple[AuditLog]]:
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if action is not None:
            query = query.where(AuditLog.action == action)
        if resource is not None:
            query = query.where(AuditLog.resource == resource)
        if created_from is not None:
            query = query.where(AuditLog.created_at >= created_from)
        if created_to is not None:
            query = query.where(AuditLog.created_at <= created_to)
        return query

import uuid
from datetime import datetime

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository


class AdminAuditLogService:
    """Read-only admin access to `AuditLog` (Phase 8F, docs/59 §11,
    ADR-129). Mirrors `AdminUserService`'s shape: constructor-injected
    repositories, one public method per use case. Deliberately has no
    create/update/delete method - the write side already exists (Phase
    2B's `AuthenticationService`, Phase 8C's `AdminUserService`), and an
    audit trail that could be mutated or deleted through its own read API
    would defeat the purpose of keeping one."""

    def __init__(
        self, audit_log_repository: AuditLogRepository, user_repository: UserRepository
    ) -> None:
        self._audit_log_repository = audit_log_repository
        self._user_repository = user_repository

    def list_logs(
        self,
        *,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[AuditLog], dict[uuid.UUID, tuple[str, str]], int]:
        """Returns the page of rows, an `{actor_id: (email, username)}`
        lookup for every distinct actor on the page (batched via
        `UserRepository.list_by_ids` - one query, not one per row), and
        the total count. A row with `user_id=None` (no actor) simply has
        no entry in the lookup; the caller renders that explicitly rather
        than crashing on a missing key."""
        offset = (page - 1) * limit
        items = list(
            self._audit_log_repository.list_admin(
                user_id=user_id,
                action=action,
                resource=resource,
                created_from=created_from,
                created_to=created_to,
                offset=offset,
                limit=limit,
            )
        )
        total = self._audit_log_repository.count_admin(
            user_id=user_id,
            action=action,
            resource=resource,
            created_from=created_from,
            created_to=created_to,
        )

        actor_ids = {log.user_id for log in items if log.user_id is not None}
        actors = self._user_repository.list_by_ids(list(actor_ids))
        actor_lookup = {actor.id: (actor.email, actor.username) for actor in actors}

        return items, actor_lookup, total

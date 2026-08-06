"""`GET /admin/logs` (Phase 8F, docs/59 §11, ADR-129). Mirrors
`admin_users.py`'s structure - flat route module, same pagination
convention (`page`/`limit`, `{"items", "page", "limit", "total"}`
envelope) as `GET /admin/users`.

Read-only by design: no route here can create, update, or delete an
audit log (`AdminAuditLogService` itself has no such method either)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies.admin import get_admin_audit_log_service
from app.dependencies.rbac import require_admin
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.admin_audit_log_service import AdminAuditLogService

router = APIRouter(prefix="/admin/logs", tags=["admin"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminAuditLogService, Depends(get_admin_audit_log_service)],
    user_id: Annotated[UUID | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    resource: Annotated[str | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AuditLogListResponse:
    items, actor_lookup, total = service.list_logs(
        user_id=user_id,
        action=action,
        resource=resource,
        created_from=from_,
        created_to=to,
        page=page,
        limit=limit,
    )
    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                actor_email=actor_lookup[log.user_id][0] if log.user_id in actor_lookup else None,
                actor_username=(
                    actor_lookup[log.user_id][1] if log.user_id in actor_lookup else None
                ),
                action=log.action,
                resource=log.resource,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                context=log.context,
                created_at=log.created_at,
            )
            for log in items
        ],
        page=page,
        limit=limit,
        total=total,
    )

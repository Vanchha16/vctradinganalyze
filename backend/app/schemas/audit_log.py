import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """`GET /admin/logs` (Phase 8F, ADR-129, docs/59 §11) - the contract is
    inferred beyond docs/04's bare path listing. `actor_email`/`actor_
    username` are resolved server-side (`AdminAuditLogService`) so the
    frontend never has to fetch a user per row; both are `None` when
    `user_id` is `None` (no actor - e.g. a failed login before the user
    resolved, or a since-deleted user whose row now has `user_id=NULL` via
    `ON DELETE SET NULL`)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b",
                "user_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                "actor_email": "admin@example.com",
                "actor_username": "admin",
                "action": "admin_role_changed",
                "resource": "user",
                "resource_id": "a3551294-154b-4ac7-a3fe-58edb2653a5f",
                "ip_address": "127.0.0.1",
                "context": {"old": {"role": "registered"}, "new": {"role": "premium"}},
                "created_at": "2026-08-06T12:00:00Z",
            }
        }
    )

    id: uuid.UUID
    user_id: uuid.UUID | None
    actor_email: str | None
    actor_username: str | None
    action: str
    resource: str
    resource_id: uuid.UUID | None
    ip_address: str | None
    context: dict[str, Any] | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])

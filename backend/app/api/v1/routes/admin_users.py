"""docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md §6.2 (Phase 8C).

Flat `admin_users.py` (not an `admin/` sub-package as originally sketched in
docs/59 §3) - every other route module in this project is a single flat
file (`telegram.py`, `signals.py`, etc.); introducing the first sub-package
for one route group would be inconsistent with that established convention
for zero behavioral benefit. Purely organizational, not a scope change.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.dependencies.admin import get_admin_user_service
from app.dependencies.rbac import require_admin, require_super_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin import (
    AdminPasswordResetResponse,
    AdminUserCreateRequest,
    AdminUserCreateResponse,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserRoleUpdateRequest,
    AdminUserStatusUpdateRequest,
    AdminUserUpdateRequest,
)
from app.services.admin_user_service import AdminUserService

router = APIRouter(prefix="/admin/users", tags=["admin"])

_Service = Annotated[AdminUserService, Depends(get_admin_user_service)]


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
    search: Annotated[str | None, Query()] = None,
    role: Annotated[UserRole | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    include_deleted: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminUserListResponse:
    """`include_deleted=True` requires `require_super_admin` in practice -
    enforced in `AdminUserService.list_users`, not here, per "business
    logic stays in the service layer"."""
    items, total = service.list_users(
        actor,
        search=search,
        role=role,
        is_active=is_active,
        include_deleted=include_deleted,
        page=page,
        limit=limit,
    )
    return AdminUserListResponse(
        items=[AdminUserResponse.model_validate(u) for u in items],
        page=page,
        limit=limit,
        total=total,
    )


@router.post("", response_model=AdminUserCreateResponse, status_code=201)
async def create_user(
    payload: AdminUserCreateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AdminUserCreateResponse:
    user, temporary_password = service.create_user(
        actor,
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        password=payload.password,
        ip_address=_client_ip(request),
    )
    return AdminUserCreateResponse(
        **AdminUserResponse.model_validate(user).model_dump(),
        temporary_password=temporary_password,
    )


@router.get("/{user_id}", response_model=AdminUserDetailResponse)
async def get_user(
    user_id: UUID,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AdminUserDetailResponse:
    user, active_session_count = service.get_user_detail(actor, user_id)
    return AdminUserDetailResponse(
        **AdminUserResponse.model_validate(user).model_dump(),
        active_session_count=active_session_count,
    )


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AdminUserResponse:
    user = service.update_user(
        actor,
        user_id,
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        ip_address=_client_ip(request),
    )
    return AdminUserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> None:
    service.delete_user(actor, user_id, ip_address=_client_ip(request))


@router.post("/{user_id}/reset-password", response_model=AdminPasswordResetResponse)
async def reset_password(
    user_id: UUID,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AdminPasswordResetResponse:
    temporary_password = service.reset_password(actor, user_id, ip_address=_client_ip(request))
    return AdminPasswordResetResponse(temporary_password=temporary_password)


@router.patch("/{user_id}/status", response_model=AdminUserResponse)
async def set_status(
    user_id: UUID,
    payload: AdminUserStatusUpdateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AdminUserResponse:
    user = service.set_status(
        actor, user_id, is_active=payload.is_active, ip_address=_client_ip(request)
    )
    return AdminUserResponse.model_validate(user)


@router.patch("/{user_id}/role", response_model=AdminUserResponse)
async def change_role(
    user_id: UUID,
    payload: AdminUserRoleUpdateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> AdminUserResponse:
    """`require_super_admin` (not `require_admin`) - role changes are
    isolated to this endpoint specifically so the escalation guard has one
    enforcement point (docs/59 §6.2)."""
    user = service.change_role(
        actor, user_id, new_role=payload.role, ip_address=_client_ip(request)
    )
    return AdminUserResponse.model_validate(user)

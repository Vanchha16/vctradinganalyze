"""Strategy and signal settings editable at runtime (ADR-178).

Super-admin only - the same boundary as EA tokens (ADR-161), because these
values change what the EA trades. Every change is audit-logged, and a change
reaches every process within the overlay's cache window without a restart.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.client_ip import get_client_ip
from app.dependencies.admin import get_admin_runtime_settings_service
from app.dependencies.rbac import require_super_admin
from app.models.user import User
from app.schemas.admin_runtime_settings import (
    RuntimeSettingListResponse,
    RuntimeSettingResponse,
    RuntimeSettingUpdateRequest,
)
from app.services import runtime_settings
from app.services.admin_runtime_settings_service import (
    AdminRuntimeSettingsService,
    RuntimeSettingStatus,
)

router = APIRouter(prefix="/admin/runtime-settings", tags=["admin"])

_Service = Annotated[AdminRuntimeSettingsService, Depends(get_admin_runtime_settings_service)]


@router.get("", response_model=RuntimeSettingListResponse)
async def list_runtime_settings(
    _actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> RuntimeSettingListResponse:
    return _response(service.list_status())


@router.put("", response_model=RuntimeSettingListResponse)
async def update_runtime_settings(
    payload: RuntimeSettingUpdateRequest,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
    request: Request,
) -> RuntimeSettingListResponse:
    """Apply a batch. Validated as a whole - an invalid batch changes
    nothing - and `null` resets a setting to its `.env` value."""
    return _response(service.apply(actor, payload.changes, ip_address=get_client_ip(request)))


def _response(statuses: list[RuntimeSettingStatus]) -> RuntimeSettingListResponse:
    return RuntimeSettingListResponse(
        propagation_seconds=runtime_settings.PROPAGATION_SECONDS,
        items=[
            RuntimeSettingResponse(
                key=s.spec.field,
                group=s.spec.group,
                label=s.spec.label,
                help=s.spec.help,
                kind=s.spec.kind,
                value=s.spec.to_json(s.value),
                default=s.spec.to_json(s.default),
                overridden=s.overridden,
                minimum=str(s.spec.minimum) if s.spec.minimum is not None else None,
                maximum=str(s.spec.maximum) if s.spec.maximum is not None else None,
                choices=list(s.spec.choices),
                updated_at=s.updated_at,
            )
            for s in statuses
        ],
    )

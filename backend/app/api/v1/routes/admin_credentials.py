"""Admin API-key management (ADR-156).

Super-admin only, matching the precedent set by role changes: these
routes write credentials that every outbound integration then uses, so
the blast radius of a compromised account is higher here than for the
rest of `/admin/*`.

No route in this module can read a stored key back. `GET` reports status
and a four-character hint; there is deliberately no reveal endpoint.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core import credential_crypto
from app.core.client_ip import get_client_ip
from app.dependencies.admin import get_admin_credential_service
from app.dependencies.rbac import require_super_admin
from app.exceptions import ResourceNotFoundException
from app.models.user import User
from app.schemas.admin_credential import (
    ApiCredentialListResponse,
    ApiCredentialResponse,
    ApiCredentialUpdateRequest,
)
from app.services.admin_credential_service import AdminCredentialService
from app.services.credential_resolver import FALLBACK_SETTING, CredentialName

router = APIRouter(prefix="/admin/credentials", tags=["admin"])

_Service = Annotated[AdminCredentialService, Depends(get_admin_credential_service)]


@router.get("", response_model=ApiCredentialListResponse)
async def list_credentials(
    _actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> ApiCredentialListResponse:
    """Status of every managed key - never a value.

    `storage_enabled` tells the UI whether editing is possible at all: with
    no `CREDENTIAL_ENCRYPTION_KEY` set there is nothing to encrypt with, so
    the form must explain that rather than fail on submit.
    """
    return ApiCredentialListResponse(
        storage_enabled=credential_crypto.is_configured(),
        items=[
            ApiCredentialResponse(
                name=s.name,
                description=s.description,
                is_set=s.is_set,
                source=s.source,
                hint=s.hint,
                updated_at=s.updated_at,
                updated_by=s.updated_by,
            )
            for s in service.list_status()
        ],
    )


@router.put("/{name}", response_model=ApiCredentialResponse)
async def set_credential(
    name: str,
    payload: ApiCredentialUpdateRequest,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
    request: Request,
) -> ApiCredentialResponse:
    """Store or replace one key.

    Takes effect on the next provider construction - within
    `credential_resolver`'s short cache window - without a restart.
    """
    credential_name = _validated_name(name)
    service.set_credential(
        actor, credential_name, payload.value, ip_address=get_client_ip(request)
    )
    return _status_for(service, credential_name)


@router.delete("/{name}", response_model=ApiCredentialResponse)
async def clear_credential(
    name: str,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
    request: Request,
) -> ApiCredentialResponse:
    """Remove the stored override so the key falls back to `.env`.

    Not the same as saving an empty value - this is the only way back to
    the environment once a key has been stored.
    """
    credential_name = _validated_name(name)
    service.clear_credential(actor, credential_name, ip_address=get_client_ip(request))
    return _status_for(service, credential_name)


def _validated_name(name: str) -> CredentialName:
    """404 for anything outside the managed set, rather than creating an
    arbitrary row: this table is a fixed list of integrations, not a
    key/value store."""
    if name not in FALLBACK_SETTING:
        raise ResourceNotFoundException(f"Unknown credential: {name}")
    return name


def _status_for(service: AdminCredentialService, name: CredentialName) -> ApiCredentialResponse:
    match = next(s for s in service.list_status() if s.name == name)
    return ApiCredentialResponse(
        name=match.name,
        description=match.description,
        is_set=match.is_set,
        source=match.source,
        hint=match.hint,
        updated_at=match.updated_at,
        updated_by=match.updated_by,
    )


__all__ = ["router"]

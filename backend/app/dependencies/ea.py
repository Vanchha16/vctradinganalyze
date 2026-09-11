from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.ea_execution_event_repository import EaExecutionEventRepository
from app.repositories.ea_token_repository import EaTokenRepository
from app.repositories.signal_repository import SignalRepository
from app.services.ea_event_service import EaEventService
from app.services.ea_service import EaPrincipal, EaService


def get_ea_service(db: Annotated[Session, Depends(get_db)]) -> EaService:
    return EaService(
        token_repository=EaTokenRepository(db),
        signal_repository=SignalRepository(db),
        asset_repository=AssetRepository(db),
        audit_log_repository=AuditLogRepository(db),
    )


def get_ea_event_service(db: Annotated[Session, Depends(get_db)]) -> EaEventService:
    return EaEventService(
        event_repository=EaExecutionEventRepository(db),
        signal_repository=SignalRepository(db),
    )


def get_ea_principal(
    service: Annotated[EaService, Depends(get_ea_service)],
    x_ea_token: Annotated[str | None, Header(alias="X-EA-Token")] = None,
) -> EaPrincipal:
    """Authenticates an Expert Advisor by its `X-EA-Token` header (ADR-161).

    A header rather than `Authorization: Bearer`, so an EA token can never
    be mistaken for - or accepted as - a session JWT by `get_current_user`,
    and a session JWT can never be accepted here.
    """
    return service.authenticate(x_ea_token, datetime.now(UTC))


def get_ea_user(principal: Annotated[EaPrincipal, Depends(get_ea_principal)]) -> User:
    return principal.user

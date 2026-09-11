from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.repositories.asset_repository import AssetRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.ea_execution_event_repository import EaExecutionEventRepository
from app.repositories.ea_token_repository import EaTokenRepository
from app.repositories.signal_repository import SignalRepository
from app.services.ea_event_service import EaEventService
from app.services.ea_service import EaPrincipal, EaService, TerminalReport


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
    x_ea_version: Annotated[str | None, Header(alias="X-EA-Version")] = None,
    x_ea_max_lot: Annotated[str | None, Header(alias="X-EA-Max-Lot")] = None,
    x_ea_allow_live: Annotated[str | None, Header(alias="X-EA-Allow-Live")] = None,
    x_ea_settings_version: Annotated[str | None, Header(alias="X-EA-Settings-Version")] = None,
    x_ea_dry_run: Annotated[str | None, Header(alias="X-EA-Dry-Run")] = None,
    x_ea_paused: Annotated[str | None, Header(alias="X-EA-Paused")] = None,
) -> EaPrincipal:
    """Authenticates an Expert Advisor by its `X-EA-Token` header (ADR-161).

    A header rather than `Authorization: Bearer`, so an EA token can never
    be mistaken for - or accepted as - a session JWT by `get_current_user`,
    and a session JWT can never be accepted here.

    The other `X-EA-*` headers are what the terminal reports about itself
    (ADR-163). They are parsed leniently: a missing or garbled one becomes
    None and never fails a request an EA depends on for its signals.
    """
    report = TerminalReport(
        ea_version=_text(x_ea_version, 16),
        max_lot=_lot(x_ea_max_lot),
        allow_remote_live=_flag(x_ea_allow_live),
        applied_settings_version=_count(x_ea_settings_version),
        dry_run=_flag(x_ea_dry_run),
        paused=_flag(x_ea_paused),
    )
    return service.authenticate(x_ea_token, datetime.now(UTC), report)


def _text(value: str | None, max_length: int) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()[:max_length]


def _flag(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true"}:
        return True
    if normalized in {"0", "false"}:
        return False
    return None


#: `applied_settings_version` is a 32-bit INTEGER column on Postgres.
_MAX_INT32 = 2_147_483_647


def _count(value: str | None) -> int | None:
    if value is None or not value.strip().isdigit():
        return None
    number = int(value.strip())
    # Out of range would fail the write - and with it the EA's poll - so it is
    # ignored like any other unreadable header.
    return number if number <= _MAX_INT32 else None


def _lot(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        lot = Decimal(value.strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    return lot if Decimal("0") < lot <= Decimal("100") else None

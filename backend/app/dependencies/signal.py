from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.ai_orchestrator import get_ai_orchestrator_engine
from app.dependencies.database import get_db
from app.dependencies.execution import get_order_execution_service
from app.repositories.signal_bookmark_repository import SignalBookmarkRepository
from app.repositories.signal_repository import SignalRepository
from app.services.ai_orchestrator_engine import AIOrchestratorEngine
from app.services.execution.order_execution_service import OrderExecutionService
from app.services.signal_engine import SignalEngine


def get_signal_repository(db: Annotated[Session, Depends(get_db)]) -> SignalRepository:
    return SignalRepository(db)


def get_signal_bookmark_repository(
    db: Annotated[Session, Depends(get_db)],
) -> SignalBookmarkRepository:
    return SignalBookmarkRepository(db)


def get_signal_engine(
    ai_orchestrator_engine: Annotated[AIOrchestratorEngine, Depends(get_ai_orchestrator_engine)],
    signal_repository: Annotated[SignalRepository, Depends(get_signal_repository)],
    execution_service: Annotated[OrderExecutionService, Depends(get_order_execution_service)],
) -> SignalEngine:
    """Composes `SignalEngine` (docs/51 §1, ADR-085) - no new provider/
    repository wiring beyond the already-existing AI Orchestrator
    dependency chain, mirroring `app/dependencies/ai_orchestrator.py`'s
    composition-only shape. `execution_service` (EA Bot spec §3G) is
    always wired in, but is a no-op beyond a dry-run log unless
    `settings.execution_enabled=True` (§0.6/§0.9) - safe by default."""
    return SignalEngine(
        ai_orchestrator_engine=ai_orchestrator_engine,
        signal_repository=signal_repository,
        execution_service=execution_service,
    )

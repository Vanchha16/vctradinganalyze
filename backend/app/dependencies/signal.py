from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.ai_orchestrator import get_ai_orchestrator_engine
from app.dependencies.database import get_db
from app.repositories.signal_bookmark_repository import SignalBookmarkRepository
from app.repositories.signal_repository import SignalRepository
from app.services.ai_orchestrator_engine import AIOrchestratorEngine
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
) -> SignalEngine:
    """Composes `SignalEngine` (docs/51 §1, ADR-085) - no new provider/
    repository wiring beyond the already-existing AI Orchestrator
    dependency chain, mirroring `app/dependencies/ai_orchestrator.py`'s
    composition-only shape."""
    return SignalEngine(
        ai_orchestrator_engine=ai_orchestrator_engine,
        signal_repository=signal_repository,
    )

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.ai_orchestrator import (
    get_ai_analysis_repository,
    get_ai_provider,
    get_context_builder,
)
from app.dependencies.database import get_db
from app.dependencies.market_data import get_asset_repository
from app.dependencies.signal import get_signal_repository
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.signal_repository import SignalRepository
from app.services.ai_chat_engine import AIChatEngine
from app.services.ai_orchestrator.context_builder import ContextBuilder
from app.services.ai_orchestrator.providers.base import AIProvider


def get_conversation_repository(
    db: Annotated[Session, Depends(get_db)],
) -> ConversationRepository:
    return ConversationRepository(db)


def get_message_repository(db: Annotated[Session, Depends(get_db)]) -> MessageRepository:
    return MessageRepository(db)


def get_ai_chat_engine(
    context_builder: Annotated[ContextBuilder, Depends(get_context_builder)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    ai_analysis_repository: Annotated[AIAnalysisRepository, Depends(get_ai_analysis_repository)],
    signal_repository: Annotated[SignalRepository, Depends(get_signal_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
) -> AIChatEngine:
    """Composes `AIChatEngine` (docs/52 §2, ADR-093) - reuses the exact
    same `ContextBuilder`/`AIProvider` dependency chain Phase 6A already
    wires (`app/dependencies/ai_orchestrator.py`), no new provider/engine
    wiring beyond the two new read-only repositories."""
    return AIChatEngine(
        context_builder=context_builder,
        provider=provider,
        asset_repository=asset_repository,
        ai_analysis_repository=ai_analysis_repository,
        signal_repository=signal_repository,
        message_repository=message_repository,
    )

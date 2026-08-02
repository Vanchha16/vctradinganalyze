"""Top-level AI Chat Assistant engine (docs/22, docs/52).

Conversational only - never computes a new recommendation, confidence
score, risk level, or any other evidence field (ADR-094). Grounding
reuses `ContextBuilder` (Phase 6A, ADR-093) for Technical/SMC/Regime/
Confidence/News/Economic/Strategy/Risk, and the most recent persisted
`ai_analysis`/`signals` rows for "why is this a BUY"/"explain this
signal" questions - no new evidence-gathering code anywhere in this
module.
"""

import logging

from app.config import settings
from app.exceptions import ResourceNotFoundException
from app.models.conversation import Conversation
from app.models.enums import MessageRole, Timeframe
from app.models.message import Message
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.signal_repository import SignalRepository

from .ai_chat import chat_prompt_builder
from .ai_chat.types import ChatExchange
from .ai_orchestrator.context_builder import ContextBuilder
from .ai_orchestrator.providers.base import AIChatRequest, AIProvider
from .ai_orchestrator.providers.exceptions import AIProviderError, TransientAIProviderError

logger = logging.getLogger(__name__)

_DEFAULT_TIMEFRAME = Timeframe.H1
_FALLBACK_REPLY = "I'm unable to generate a response right now. Please try again shortly."


class AIChatEngine:
    def __init__(
        self,
        context_builder: ContextBuilder,
        provider: AIProvider,
        asset_repository: AssetRepository,
        ai_analysis_repository: AIAnalysisRepository,
        signal_repository: SignalRepository,
        message_repository: MessageRepository,
    ) -> None:
        self._context_builder = context_builder
        self._provider = provider
        self._asset_repository = asset_repository
        self._ai_analysis_repository = ai_analysis_repository
        self._signal_repository = signal_repository
        self._message_repository = message_repository

    def send_message(
        self,
        conversation: Conversation,
        content: str,
        *,
        symbol: str | None = None,
        timeframe: Timeframe | None = None,
    ) -> ChatExchange:
        resolved_symbol = (symbol or conversation.current_symbol or "").upper() or None
        resolved_timeframe = timeframe or conversation.current_timeframe
        if resolved_symbol is not None and resolved_timeframe is None:
            resolved_timeframe = _DEFAULT_TIMEFRAME

        context = None
        latest_analysis = None
        latest_signal = None

        if resolved_symbol is not None:
            asset = self._asset_repository.get_by_symbol(resolved_symbol)
            if asset is None:
                raise ResourceNotFoundException(f"Unknown asset symbol: {resolved_symbol}")

            assert resolved_timeframe is not None
            context = self._context_builder.build(asset, resolved_timeframe)

            analyses = self._ai_analysis_repository.find_paginated(
                asset_id=asset.id, timeframe=resolved_timeframe, limit=1
            )
            latest_analysis = analyses[0] if analyses else None

            signals = self._signal_repository.find_paginated(
                asset_id=asset.id, timeframe=resolved_timeframe, limit=1
            )
            latest_signal = signals[0] if signals else None

            conversation.current_symbol = resolved_symbol
            conversation.current_timeframe = resolved_timeframe

        history = self._message_repository.list_recent(
            conversation.id, limit=settings.chat_max_history_messages
        )

        request = chat_prompt_builder.build(
            history=history,
            question=content,
            context=context,
            latest_analysis=latest_analysis,
            latest_signal=latest_signal,
        )

        reply_text, model_name, ai_available, warnings = self._generate_reply(request)

        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
            symbol=resolved_symbol,
            timeframe=resolved_timeframe,
        )
        self._message_repository.create(user_message)

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=reply_text,
            symbol=resolved_symbol,
            timeframe=resolved_timeframe,
            ai_analysis_id=latest_analysis.id if latest_analysis is not None else None,
            signal_id=latest_signal.id if latest_signal is not None else None,
            model_name=model_name if ai_available else None,
            prompt_version=chat_prompt_builder.CHAT_PROMPT_VERSION,
        )
        self._message_repository.create(assistant_message)

        if conversation.title is None:
            conversation.title = content[:60]

        self._message_repository.commit()

        return ChatExchange(
            user_message=user_message, assistant_message=assistant_message, warnings=warnings
        )

    def _generate_reply(self, request: AIChatRequest) -> tuple[str, str, bool, list[str]]:
        warnings: list[str] = []
        last_error: Exception | None = None

        for attempt in range(1, settings.ai_retry_max_attempts + 1):
            try:
                response = self._provider.generate_chat_reply(request)
                return response.content, response.model_name, True, warnings
            except AIProviderError as exc:
                last_error = exc
                logger.warning(
                    "ai_chat.provider_call_failed",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                if not isinstance(exc, TransientAIProviderError):
                    break
                continue

        warnings.append(f"AI reply unavailable ({last_error}).")
        return _FALLBACK_REPLY, "none", False, warnings

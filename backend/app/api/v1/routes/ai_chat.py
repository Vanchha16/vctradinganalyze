from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.dependencies.ai_chat import (
    get_ai_chat_engine,
    get_conversation_repository,
    get_message_repository,
)
from app.exceptions import ResourceNotFoundException
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.ai_chat import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.ai_chat_engine import AIChatEngine

router = APIRouter(tags=["ai-chat"])


def _get_owned_conversation(
    conversation_id: UUID,
    current_user: User,
    conversation_repository: ConversationRepository,
) -> Conversation:
    conversation = conversation_repository.get_by_id(conversation_id)
    if conversation is None or conversation.user_id != current_user.id:
        raise ResourceNotFoundException(f"Unknown conversation id: {conversation_id}")
    return conversation


@router.post("/chat/conversations", response_model=ConversationResponse)
async def create_conversation(
    body: CreateConversationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
) -> ConversationResponse:
    conversation = Conversation(
        user_id=current_user.id,
        current_symbol=body.symbol.upper() if body.symbol else None,
        current_timeframe=body.timeframe,
    )
    conversation_repository.create(conversation)
    conversation_repository.commit()
    return ConversationResponse.model_validate(conversation)


@router.get("/chat/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
    status: Annotated[ConversationStatus, Query()] = ConversationStatus.ACTIVE,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ConversationListResponse:
    offset = (page - 1) * limit
    rows = conversation_repository.find_paginated(
        user_id=current_user.id, status=status, offset=offset, limit=limit
    )
    total = conversation_repository.count_filtered(user_id=current_user.id, status=status)
    items = [ConversationResponse.model_validate(row) for row in rows]
    return ConversationListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/chat/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
) -> ConversationDetailResponse:
    conversation = _get_owned_conversation(conversation_id, current_user, conversation_repository)
    messages = message_repository.list_for_conversation(conversation.id)
    return ConversationDetailResponse(
        **ConversationResponse.model_validate(conversation).model_dump(),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.post("/chat/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
    engine: Annotated[AIChatEngine, Depends(get_ai_chat_engine)],
) -> SendMessageResponse:
    conversation = _get_owned_conversation(conversation_id, current_user, conversation_repository)

    exchange = engine.send_message(
        conversation,
        body.content,
        symbol=body.symbol,
        timeframe=body.timeframe,
    )

    return SendMessageResponse(
        conversation=ConversationResponse.model_validate(conversation),
        user_message=MessageResponse.model_validate(exchange.user_message),
        assistant_message=MessageResponse.model_validate(exchange.assistant_message),
        warnings=exchange.warnings,
    )


@router.post("/chat/conversations/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
) -> ConversationResponse:
    conversation = _get_owned_conversation(conversation_id, current_user, conversation_repository)
    conversation.status = ConversationStatus.ARCHIVED
    conversation_repository.commit()
    return ConversationResponse.model_validate(conversation)


@router.delete("/chat/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    conversation_repository: Annotated[
        ConversationRepository, Depends(get_conversation_repository)
    ],
) -> None:
    conversation = _get_owned_conversation(conversation_id, current_user, conversation_repository)
    conversation_repository.delete(conversation)
    conversation_repository.commit()

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConversationStatus, MessageRole, Timeframe


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    symbol: str | None
    timeframe: Timeframe | None
    ai_analysis_id: uuid.UUID | None
    signal_id: uuid.UUID | None
    model_name: str | None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    current_symbol: str | None
    current_timeframe: Timeframe | None
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])


class CreateConversationRequest(BaseModel):
    symbol: str | None = None
    timeframe: Timeframe | None = None


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    symbol: str | None = None
    timeframe: Timeframe | None = None


class SendMessageResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation": {
                    "id": "3f7e2b1a-9c4d-4e5f-8a6b-1d2c3e4f5a6b",
                    "title": "Why is this a BUY?",
                    "current_symbol": "EURUSD",
                    "current_timeframe": "h1",
                    "status": "active",
                    "created_at": "2026-08-02T12:00:00Z",
                    "updated_at": "2026-08-02T12:00:05Z",
                },
                "user_message": {
                    "id": "...",
                    "role": "user",
                    "content": "Why is this a BUY?",
                    "symbol": "EURUSD",
                    "timeframe": "h1",
                },
                "assistant_message": {
                    "id": "...",
                    "role": "assistant",
                    "content": "The current recommendation is BUY because...",
                    "symbol": "EURUSD",
                    "timeframe": "h1",
                    "ai_analysis_id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                    "signal_id": None,
                    "model_name": "gpt-4o-mini",
                },
                "warnings": [],
            }
        }
    )

    conversation: ConversationResponse
    user_message: MessageResponse
    assistant_message: MessageResponse
    warnings: list[str]

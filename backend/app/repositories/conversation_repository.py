import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.enums import ConversationStatus
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    def create(self, conversation: Conversation) -> Conversation:
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def find_paginated(
        self,
        *,
        user_id: uuid.UUID,
        status: ConversationStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Conversation]:
        query = select(Conversation).where(Conversation.user_id == user_id)
        if status is not None:
            query = query.where(Conversation.status == status)
        query = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(
        self, *, user_id: uuid.UUID, status: ConversationStatus | None = None
    ) -> int:
        query = select(Conversation).where(Conversation.user_id == user_id)
        if status is not None:
            query = query.where(Conversation.status == status)
        return self._count(query)

    def delete(self, conversation: Conversation) -> None:
        self.session.delete(conversation)
        self.session.flush()

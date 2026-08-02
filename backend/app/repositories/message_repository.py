import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    model = Message

    def create(self, message: Message) -> Message:
        self.session.add(message)
        self.session.flush()
        return message

    def list_for_conversation(
        self, conversation_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Message]:
        """Chronological (oldest first) - the natural reading order for a
        conversation transcript, unlike every other list endpoint in this
        project (which lists newest-first)."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.execute(query).scalars().all()

    def list_recent(self, conversation_id: uuid.UUID, *, limit: int) -> Sequence[Message]:
        """Most recent `limit` messages, chronological order - the
        multi-turn history window fed to the model (docs/52 §7)."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(query).scalars().all()
        return list(reversed(rows))

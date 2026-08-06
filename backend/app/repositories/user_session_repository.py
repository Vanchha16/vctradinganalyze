import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import CursorResult, delete, func, select

from app.models.user_session import UserSession
from app.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSession]):
    model = UserSession

    def get_by_id(self, session_id: uuid.UUID) -> UserSession | None:
        return self.session.get(UserSession, session_id)

    def get_by_refresh_token_hash(self, refresh_token_hash: str) -> UserSession | None:
        query = self._filter_by(self._query(), refresh_token_hash=refresh_token_hash)
        return self.session.execute(query).scalar_one_or_none()

    def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> Sequence[UserSession]:
        query = self._filter_by(self._query(), user_id=user_id)
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def create(self, session_: UserSession) -> UserSession:
        self.session.add(session_)
        self.session.flush()
        return session_

    def delete(self, session_: UserSession) -> None:
        self.session.delete(session_)

    def count_for_user(self, user_id: uuid.UUID) -> int:
        """Active session count for the Admin user-detail view (docs/59 §6.2)."""
        query = self._filter_by(self._query(), user_id=user_id)
        return self._count(query)

    def delete_for_user(self, user_id: uuid.UUID, *, exclude_id: uuid.UUID | None = None) -> int:
        """Delete all sessions for a user, optionally keeping one (e.g. the current session)."""
        stmt = delete(UserSession).where(UserSession.user_id == user_id)
        if exclude_id is not None:
            stmt = stmt.where(UserSession.id != exclude_id)
        result = cast(CursorResult[UserSession], self.session.execute(stmt))
        return result.rowcount or 0

    def count_distinct_users_since(self, since: datetime) -> int:
        """Daily active users (docs/58 §3.2, Phase 7D-C) - a session's
        `created_at` is its login time, so distinct `user_id` values with a
        session created since `since` approximates "logged in today."
        Distinct at the SQL level rather than counting rows, since a user
        may log in more than once."""
        query = select(func.count(func.distinct(UserSession.user_id))).where(
            UserSession.created_at >= since
        )
        return self.session.execute(query).scalar_one()

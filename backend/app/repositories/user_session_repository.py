import uuid
from collections.abc import Sequence

from app.models.user_session import UserSession
from app.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSession]):
    model = UserSession

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

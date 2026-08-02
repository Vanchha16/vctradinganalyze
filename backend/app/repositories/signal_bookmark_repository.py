import uuid

from app.models.signal_bookmark import SignalBookmark
from app.repositories.base import BaseRepository


class SignalBookmarkRepository(BaseRepository[SignalBookmark]):
    model = SignalBookmark

    def create(self, bookmark: SignalBookmark) -> SignalBookmark:
        self.session.add(bookmark)
        self.session.flush()
        return bookmark

    def get_by_id(self, bookmark_id: uuid.UUID) -> SignalBookmark | None:
        return self.session.get(SignalBookmark, bookmark_id)

    def get_by_user_and_signal(
        self, user_id: uuid.UUID, signal_id: uuid.UUID
    ) -> SignalBookmark | None:
        query = self._query().filter_by(user_id=user_id, signal_id=signal_id)
        return self.session.execute(query).scalar_one_or_none()

    def delete(self, bookmark: SignalBookmark) -> None:
        self.session.delete(bookmark)
        self.session.flush()

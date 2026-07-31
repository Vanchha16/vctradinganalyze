from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        query = self._filter_by(self._query(), email=email)
        return self.session.execute(query).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        query = self._filter_by(self._query(), username=username)
        return self.session.execute(query).scalar_one_or_none()

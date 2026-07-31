import uuid

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        query = self._filter_by(self._query(), email=email)
        return self.session.execute(query).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        query = self._filter_by(self._query(), username=username)
        return self.session.execute(query).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

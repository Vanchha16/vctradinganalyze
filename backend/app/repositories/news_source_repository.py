from collections.abc import Sequence

from app.models.news_source import NewsSource
from app.repositories.base import BaseRepository


class NewsSourceRepository(BaseRepository[NewsSource]):
    model = NewsSource

    def create(self, source: NewsSource) -> NewsSource:
        self.session.add(source)
        self.session.flush()
        return source

    def find_by_name(self, name: str) -> NewsSource | None:
        query = self._filter_by(self._query(), name=name)
        return self.session.execute(query).scalar_one_or_none()

    def find_active(self) -> Sequence[NewsSource]:
        query = self._filter_by(self._query(), is_active=True)
        return self.session.execute(query).scalars().all()

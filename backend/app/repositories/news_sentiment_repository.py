import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from app.models.news_article import NewsArticle
from app.models.news_sentiment import NewsSentiment
from app.repositories.base import BaseRepository


class NewsSentimentRepository(BaseRepository[NewsSentiment]):
    model = NewsSentiment

    def create(self, sentiment: NewsSentiment) -> NewsSentiment:
        self.session.add(sentiment)
        self.session.flush()
        return sentiment

    def find_by_article_id(self, article_id: uuid.UUID) -> NewsSentiment | None:
        query = self._filter_by(self._query(), article_id=article_id)
        return self.session.execute(query).scalar_one_or_none()

    def find_by_asset_since(self, symbol: str, since: datetime) -> Sequence[NewsSentiment]:
        """Sentiment rows for articles published at/after `since` whose
        `affected_assets` includes `symbol` (docs/46 §3's read path,
        backs `GET /analysis/news/{symbol}`).

        Filtered in Python rather than a DB-specific JSON containment
        operator - `affected_assets` is a small JSON list and this
        project targets both SQLite (tests) and PostgreSQL (prod), so a
        portable filter avoids diverging query logic per dialect for a
        query pattern this small.
        """
        query = (
            select(NewsSentiment)
            .join(NewsArticle, NewsSentiment.article_id == NewsArticle.id)
            .where(NewsArticle.published_at >= since)
            .order_by(NewsArticle.published_at.desc())
        )
        rows = self.session.execute(query).scalars().all()
        return [row for row in rows if symbol in row.affected_assets]

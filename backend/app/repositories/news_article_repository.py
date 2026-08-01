import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.models.enums import NewsCategory, NewsImportance
from app.models.news_article import NewsArticle
from app.repositories.base import BaseRepository


class NewsArticleRepository(BaseRepository[NewsArticle]):
    model = NewsArticle

    def create(self, article: NewsArticle) -> NewsArticle:
        self.session.add(article)
        self.session.flush()
        return article

    def get_by_id(self, article_id: uuid.UUID) -> NewsArticle | None:
        return self.session.get(NewsArticle, article_id)

    def find_by_url(self, url: str) -> NewsArticle | None:
        query = self._filter_by(self._query(), url=url)
        return self.session.execute(query).scalar_one_or_none()

    def find_recent(self, *, since: datetime, limit: int = 200) -> Sequence[NewsArticle]:
        """Recently ingested articles, used by `dedup_detector` to compare
        a candidate against - bounded by `limit` since dedup only needs a
        recent window, not the entire history (docs/46 §7)."""
        query = (
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        return self.session.execute(query).scalars().all()

    def find_paginated(
        self,
        *,
        importance: NewsImportance | None = None,
        category: NewsCategory | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[NewsArticle]:
        filters = self._build_filters(importance, category)
        query = self._filter_by(self._query(), **filters).order_by(NewsArticle.published_at.desc())
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def count_filtered(
        self,
        *,
        importance: NewsImportance | None = None,
        category: NewsCategory | None = None,
    ) -> int:
        query = self._filter_by(self._query(), **self._build_filters(importance, category))
        return self._count(query)

    @staticmethod
    def _build_filters(
        importance: NewsImportance | None, category: NewsCategory | None
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if importance is not None:
            filters["importance"] = importance
        if category is not None:
            filters["category"] = category
        return filters

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NewsCategory, NewsImportance, NewsSentimentLabel


class NewsSentimentDetailResponse(BaseModel):
    """Embedded sentiment detail (docs/04 §News GET /news/{id})."""

    model_config = ConfigDict(from_attributes=True)

    sentiment: NewsSentimentLabel
    confidence: float
    reason: str
    affected_assets: list[str]
    ai_summary: str | None


class NewsArticleListItemResponse(BaseModel):
    """docs/04 §News GET /news - one row of the paginated list. Built
    explicitly by the route handler (not `model_validate(article)`
    directly) since `source`/`sentiment` are derived from relationships,
    not plain scalar attributes on `NewsArticle`."""

    id: uuid.UUID
    source: str
    title: str
    summary: str | None
    category: NewsCategory
    importance: NewsImportance
    published_at: datetime
    sentiment: NewsSentimentLabel | None
    confidence: float | None


class NewsArticleListResponse(BaseModel):
    items: list[NewsArticleListItemResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])


class NewsArticleDetailResponse(BaseModel):
    """docs/04 §News GET /news/{id}."""

    id: uuid.UUID
    source: str
    title: str
    summary: str | None
    content: str | None
    url: str
    category: NewsCategory
    importance: NewsImportance
    published_at: datetime
    sentiment: NewsSentimentDetailResponse | None

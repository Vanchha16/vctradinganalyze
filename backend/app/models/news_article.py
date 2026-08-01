import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin
from app.models.enums import NewsCategory, NewsImportance

if TYPE_CHECKING:
    from app.models.news_sentiment import NewsSentiment
    from app.models.news_source import NewsSource


class NewsArticle(Base, UUIDMixin, CreatedAtMixin):
    """A single ingested news article (docs/03 §8, docs/10, docs/46 §2).

    Uses CreatedAtMixin (not TimestampMixin) - once ingested, an
    article's own content is an append-only historical fact (ADR-053).
    `created_at` (from the mixin) is our own ingestion timestamp;
    `published_at` is the source's own publish timestamp - the two are
    deliberately distinct concepts.
    """

    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_news_articles_category_importance", "category", "importance"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("news_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True, nullable=False)
    category: Mapped[NewsCategory] = mapped_column(
        SAEnum(NewsCategory, name="news_category", native_enum=True), nullable=False
    )
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    importance: Mapped[NewsImportance] = mapped_column(
        SAEnum(NewsImportance, name="news_importance", native_enum=True), nullable=False
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped["NewsSource"] = relationship(back_populates="articles")
    sentiment: Mapped["NewsSentiment | None"] = relationship(
        back_populates="article", cascade="all, delete-orphan", uselist=False
    )

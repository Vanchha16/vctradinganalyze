from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin
from app.models.enums import NewsSourceTier

if TYPE_CHECKING:
    from app.models.news_article import NewsArticle


class NewsSource(Base, UUIDMixin, TimestampMixin):
    """A news outlet/publisher (docs/03 §8, docs/10 §3). Uses
    TimestampMixin (not CreatedAtMixin) because it's a small,
    admin-managed list - `priority`/`is_active`/`tier` can change after
    creation (ADR-053)."""

    __tablename__ = "news_sources"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    tier: Mapped[NewsSourceTier] = mapped_column(
        SAEnum(NewsSourceTier, name="news_source_tier", native_enum=True), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    articles: Mapped[list["NewsArticle"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

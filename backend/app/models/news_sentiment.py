import uuid

from sqlalchemy import JSON, Float, ForeignKey, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin
from app.models.enums import NewsSentimentLabel
from app.models.news_article import NewsArticle


class NewsSentiment(Base, UUIDMixin, TimestampMixin):
    """Sentiment evidence for one `NewsArticle` (docs/03 §8, docs/10 §7,
    docs/46 §2). Uses TimestampMixin (not CreatedAtMixin) - a sentiment
    row can be recomputed in place if scoring logic changes and
    historical articles are re-scored (ADR-053).

    One row per article (`article_id` unique), not one row per
    article-asset pair - `affected_assets` is a JSON list column instead
    of a normalized child table (ADR-052).
    """

    __tablename__ = "news_sentiment"

    article_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    sentiment: Mapped[NewsSentimentLabel] = mapped_column(
        SAEnum(NewsSentimentLabel, name="news_sentiment_label", native_enum=True), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_assets: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    article: Mapped["NewsArticle"] = relationship(back_populates="sentiment")

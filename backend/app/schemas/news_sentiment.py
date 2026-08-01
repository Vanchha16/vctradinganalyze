import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NewsCategory, NewsImportance, NewsSentimentLabel


class NewsSentimentArticleResponse(BaseModel):
    """docs/04 §News Sentiment GET /analysis/news/{symbol}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(validation_alias="article_id")
    headline: str
    category: NewsCategory
    importance: NewsImportance
    sentiment: NewsSentimentLabel
    confidence: float
    reason: str
    affected_assets: list[str]
    ai_summary: str | None
    published_at: datetime
    source: str


class NewsSentimentAnalysisResponse(BaseModel):
    """docs/46 §6 - `NewsSentimentEvidence`'s public shape. No `timeframe`
    field (docs/46 §10) - asset/time-window scoped via `since` instead."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "symbol": "XAUUSD",
                "since": "2026-07-31T00:00:00Z",
                "articles": [
                    {
                        "id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                        "headline": "Gold Prices Slide as Stronger Dollar Weighs on Bullion",
                        "category": "commodities",
                        "importance": "medium",
                        "sentiment": "bearish",
                        "confidence": 65.0,
                        "reason": "Matched 1 sentiment keyword(s): falls (score=-1.0).",
                        "affected_assets": ["XAUUSD"],
                        "ai_summary": None,
                        "published_at": "2026-07-31T06:00:00Z",
                        "source": "Forex Factory",
                    }
                ],
                "warnings": [],
                "calculated_at": "2026-08-01T12:00:00Z",
            }
        },
    )

    symbol: str
    since: datetime
    articles: list[NewsSentimentArticleResponse]
    warnings: list[str]
    calculated_at: datetime

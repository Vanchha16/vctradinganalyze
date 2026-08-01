import re
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.routes.market_data import get_asset_or_404
from app.config import settings
from app.dependencies.news import (
    get_news_article_repository,
    get_news_sentiment_engine,
)
from app.exceptions import ResourceNotFoundException, ValidationException
from app.models.asset import Asset
from app.models.enums import NewsCategory, NewsImportance
from app.models.news_article import NewsArticle
from app.repositories.news_article_repository import NewsArticleRepository
from app.schemas.news import (
    NewsArticleDetailResponse,
    NewsArticleListItemResponse,
    NewsArticleListResponse,
    NewsSentimentDetailResponse,
)
from app.schemas.news_sentiment import NewsSentimentAnalysisResponse
from app.services.news_sentiment_engine import NewsSentimentEngine

router = APIRouter(tags=["news"])

_SINCE_PATTERN = re.compile(r"^(\d+)([hd])$")


def _parse_since(since: str | None) -> datetime:
    """`since` is a relative window (`24h`, `3d`), not a `Timeframe` -
    News is asset/time-window scoped, not candle-timeframe scoped
    (docs/46 §10). Defaults to `settings.news_lookback_hours`."""
    if since is None:
        return datetime.now(UTC) - timedelta(hours=settings.news_lookback_hours)

    match = _SINCE_PATTERN.match(since)
    if match is None:
        raise ValidationException(f"Invalid `since` value: {since!r}. Expected e.g. '24h' or '3d'.")

    amount, unit = int(match.group(1)), match.group(2)
    delta = timedelta(hours=amount) if unit == "h" else timedelta(days=amount)
    return datetime.now(UTC) - delta


def _to_list_item(article: NewsArticle) -> NewsArticleListItemResponse:
    sentiment = article.sentiment
    return NewsArticleListItemResponse(
        id=article.id,
        source=article.source.name,
        title=article.title,
        summary=article.summary,
        category=article.category,
        importance=article.importance,
        published_at=article.published_at,
        sentiment=sentiment.sentiment if sentiment else None,
        confidence=sentiment.confidence if sentiment else None,
    )


@router.get("/news", response_model=NewsArticleListResponse)
async def list_news(
    article_repository: Annotated[NewsArticleRepository, Depends(get_news_article_repository)],
    importance: Annotated[NewsImportance | None, Query()] = None,
    category: Annotated[NewsCategory | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> NewsArticleListResponse:
    offset = (page - 1) * limit
    items = article_repository.find_paginated(
        importance=importance, category=category, offset=offset, limit=limit
    )
    total = article_repository.count_filtered(importance=importance, category=category)
    return NewsArticleListResponse(
        items=[_to_list_item(item) for item in items], page=page, limit=limit, total=total
    )


@router.get("/news/{article_id}", response_model=NewsArticleDetailResponse)
async def get_news_article(
    article_id: UUID,
    article_repository: Annotated[NewsArticleRepository, Depends(get_news_article_repository)],
) -> NewsArticleDetailResponse:
    article = article_repository.get_by_id(article_id)
    if article is None:
        raise ResourceNotFoundException(f"Unknown news article id: {article_id}")

    sentiment = article.sentiment
    return NewsArticleDetailResponse(
        id=article.id,
        source=article.source.name,
        title=article.title,
        summary=article.summary,
        content=article.content,
        url=article.url,
        category=article.category,
        importance=article.importance,
        published_at=article.published_at,
        sentiment=(
            NewsSentimentDetailResponse.model_validate(sentiment) if sentiment is not None else None
        ),
    )


@router.get("/analysis/news/{symbol}", response_model=NewsSentimentAnalysisResponse)
async def get_news_sentiment(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    engine: Annotated[NewsSentimentEngine, Depends(get_news_sentiment_engine)],
    since: Annotated[str | None, Query()] = None,
) -> NewsSentimentAnalysisResponse:
    since_dt = _parse_since(since)
    result = engine.get_sentiment_for_asset(asset.symbol, since_dt)
    return NewsSentimentAnalysisResponse.model_validate(result)

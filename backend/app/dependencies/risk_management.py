from typing import Annotated

from fastapi import Depends

from app.dependencies.analysis_confidence import get_analysis_confidence_engine
from app.dependencies.economic_calendar import get_economic_calendar_engine
from app.dependencies.market_data import get_asset_repository, get_price_candle_repository
from app.dependencies.news import get_news_sentiment_engine
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.news_sentiment_engine import NewsSentimentEngine
from app.services.risk_management_engine import RiskManagementEngine


def get_risk_management_engine(
    confidence_engine: Annotated[AnalysisConfidenceEngine, Depends(get_analysis_confidence_engine)],
    news_sentiment_engine: Annotated[NewsSentimentEngine, Depends(get_news_sentiment_engine)],
    economic_calendar_engine: Annotated[
        EconomicCalendarEngine, Depends(get_economic_calendar_engine)
    ],
    price_candle_repository: Annotated[PriceCandleRepository, Depends(get_price_candle_repository)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
) -> RiskManagementEngine:
    """Wires the engine this project already built for every input
    docs/12 needs (ADR-064) - no new provider/repository wiring, only
    composition of `get_analysis_confidence_engine`/`get_news_sentiment_engine`/
    `get_economic_calendar_engine`, mirroring `app/dependencies/economic_calendar.py`'s
    shape."""
    return RiskManagementEngine(
        confidence_engine=confidence_engine,
        news_sentiment_engine=news_sentiment_engine,
        economic_calendar_engine=economic_calendar_engine,
        price_candle_repository=price_candle_repository,
        asset_repository=asset_repository,
    )

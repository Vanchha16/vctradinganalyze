from typing import Annotated

from fastapi import Depends

from app.dependencies.analysis_confidence import get_analysis_confidence_engine
from app.dependencies.economic_calendar import get_economic_calendar_engine
from app.dependencies.market_data import get_price_candle_repository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.economic_calendar_engine import EconomicCalendarEngine
from app.services.strategy_engine import StrategyEngine


def get_strategy_engine(
    confidence_engine: Annotated[AnalysisConfidenceEngine, Depends(get_analysis_confidence_engine)],
    economic_calendar_engine: Annotated[
        EconomicCalendarEngine, Depends(get_economic_calendar_engine)
    ],
    price_candle_repository: Annotated[PriceCandleRepository, Depends(get_price_candle_repository)],
) -> StrategyEngine:
    """Wires the engine this project already built for every input
    docs/17 needs (ADR-071) - no new provider/repository wiring, only
    composition of `get_analysis_confidence_engine`/
    `get_economic_calendar_engine`, mirroring
    `app/dependencies/risk_management.py`'s shape."""
    return StrategyEngine(
        confidence_engine=confidence_engine,
        economic_calendar_engine=economic_calendar_engine,
        price_candle_repository=price_candle_repository,
    )

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.smc import get_smc_engine
from app.dependencies.technical_analysis import get_technical_analysis_engine
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_regime_engine import MarketRegimeEngine
from app.services.smc_engine import SMCEngine
from app.services.technical_analysis_engine import TechnicalAnalysisEngine


def get_market_regime_engine(
    db: Annotated[Session, Depends(get_db)],
    technical_analysis_engine: Annotated[
        TechnicalAnalysisEngine, Depends(get_technical_analysis_engine)
    ],
    smc_engine: Annotated[SMCEngine, Depends(get_smc_engine)],
) -> MarketRegimeEngine:
    return MarketRegimeEngine(PriceCandleRepository(db), technical_analysis_engine, smc_engine)

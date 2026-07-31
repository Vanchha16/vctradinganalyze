from typing import Annotated

from fastapi import Depends

from app.dependencies.market_regime import get_market_regime_engine
from app.dependencies.smc import get_smc_engine
from app.dependencies.technical_analysis import get_technical_analysis_engine
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine
from app.services.market_regime_engine import MarketRegimeEngine
from app.services.smc_engine import SMCEngine
from app.services.technical_analysis_engine import TechnicalAnalysisEngine


def get_analysis_confidence_engine(
    technical_analysis_engine: Annotated[
        TechnicalAnalysisEngine, Depends(get_technical_analysis_engine)
    ],
    smc_engine: Annotated[SMCEngine, Depends(get_smc_engine)],
    market_regime_engine: Annotated[MarketRegimeEngine, Depends(get_market_regime_engine)],
) -> AnalysisConfidenceEngine:
    return AnalysisConfidenceEngine(technical_analysis_engine, smc_engine, market_regime_engine)

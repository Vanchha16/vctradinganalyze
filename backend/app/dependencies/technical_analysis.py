from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.technical_analysis_engine import TechnicalAnalysisEngine


def get_technical_analysis_engine(
    db: Annotated[Session, Depends(get_db)],
) -> TechnicalAnalysisEngine:
    return TechnicalAnalysisEngine(PriceCandleRepository(db))

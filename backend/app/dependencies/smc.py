from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.smc_event_repository import SMCEventRepository
from app.repositories.smc_processing_state_repository import SMCProcessingStateRepository
from app.services.smc_engine import SMCEngine


def get_smc_engine(db: Annotated[Session, Depends(get_db)]) -> SMCEngine:
    return SMCEngine(
        PriceCandleRepository(db), SMCEventRepository(db), SMCProcessingStateRepository(db)
    )

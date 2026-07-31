from typing import Annotated

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.dependencies.market_data import get_market_data_providers

router = APIRouter()


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Return process health without depending on infrastructure services."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    """Verify the API can reach its required infrastructure (database, cache).

    Market-data provider health is reported diagnostically (docs/40) - a
    provider being unreachable does not flip the overall readiness status,
    since the rest of the API remains servable without it.
    """
    db.execute(text("SELECT 1"))

    redis_client = redis.Redis.from_url(settings.redis_url)
    redis_client.ping()

    provider_health = {
        provider.name: provider.health_check() for provider in get_market_data_providers()
    }

    return {"status": "ok", "market_data_providers": provider_health}

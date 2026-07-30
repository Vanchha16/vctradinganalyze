from typing import Annotated

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db

router = APIRouter()


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Return process health without depending on infrastructure services."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Verify the API can reach its required infrastructure (database, cache)."""
    db.execute(text("SELECT 1"))

    redis_client = redis.Redis.from_url(settings.redis_url)
    redis_client.ping()

    return {"status": "ok"}

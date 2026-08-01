from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies.economic_calendar import get_economic_calendar_engine
from app.exceptions import ResourceNotFoundException
from app.models.enums import EconomicEventCategory, EconomicEventImportance
from app.schemas.economic_calendar import (
    EconomicEventListResponse,
    EconomicEventResponse,
    EconomicEventUpcomingResponse,
)
from app.services.economic_calendar_engine import EconomicCalendarEngine

router = APIRouter(prefix="/calendar", tags=["economic-calendar"])

_DEFAULT_UPCOMING_LIMIT = 20


def _resolve_range(
    range_: Literal["today", "week"] | None, from_: datetime | None, to: datetime | None
) -> tuple[datetime | None, datetime | None]:
    """`range=today|week` is a shortcut over `from`/`to` (docs/47 §11) -
    if given, it takes precedence over explicit `from`/`to`."""
    if range_ is None:
        return from_, to

    now = datetime.now(UTC)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_ == "today":
        return start_of_today, start_of_today + timedelta(days=1)
    return start_of_today, start_of_today + timedelta(days=7)


@router.get("", response_model=EconomicEventListResponse)
async def list_calendar_events(
    engine: Annotated[EconomicCalendarEngine, Depends(get_economic_calendar_engine)],
    country: Annotated[str | None, Query()] = None,
    currency: Annotated[str | None, Query()] = None,
    importance: Annotated[EconomicEventImportance | None, Query()] = None,
    category: Annotated[EconomicEventCategory | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    range_: Annotated[Literal["today", "week"] | None, Query(alias="range")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> EconomicEventListResponse:
    start, end = _resolve_range(range_, from_, to)
    offset = (page - 1) * limit

    result, total = engine.list_events(
        country=country,
        currency=currency,
        importance=importance,
        category=category,
        start=start,
        end=end,
        offset=offset,
        limit=limit,
    )
    return EconomicEventListResponse(
        items=[EconomicEventResponse.model_validate(e) for e in result.events],
        page=page,
        limit=limit,
        total=total,
    )


@router.get("/upcoming", response_model=EconomicEventUpcomingResponse)
async def get_upcoming_calendar_events(
    engine: Annotated[EconomicCalendarEngine, Depends(get_economic_calendar_engine)],
    limit: Annotated[int, Query(ge=1, le=100)] = _DEFAULT_UPCOMING_LIMIT,
) -> EconomicEventUpcomingResponse:
    result = engine.get_upcoming(limit=limit)
    return EconomicEventUpcomingResponse(
        items=[EconomicEventResponse.model_validate(e) for e in result.events]
    )


@router.get("/{event_id}", response_model=EconomicEventResponse)
async def get_calendar_event(
    event_id: UUID,
    engine: Annotated[EconomicCalendarEngine, Depends(get_economic_calendar_engine)],
) -> EconomicEventResponse:
    evidence = engine.get_by_id(event_id)
    if evidence is None:
        raise ResourceNotFoundException(f"Unknown economic event id: {event_id}")
    return EconomicEventResponse.model_validate(evidence)

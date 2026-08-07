from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IngestionHealthResponse(BaseModel):
    """Phase 9G (ADR-139) - per-pipeline ingestion health, added to `GET
    /admin/system` after production ran with an empty news pipeline and
    a silently-mocked economic calendar with nothing surfacing either.
    `last_success_at`/`last_error` are read from Redis (fail-open, never
    the reason this endpoint 500s) - `None` means "never recorded in
    this Redis instance" (e.g. right after a fresh deploy), not
    necessarily "never succeeded"."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "providers": ["mock"],
                "uses_mock": True,
                "last_success_at": "2026-08-07T09:00:00Z",
                "last_error": None,
            }
        }
    )

    providers: list[str]
    uses_mock: bool
    last_success_at: datetime | None
    last_error: str | None


class AdminSystemStatusResponse(BaseModel):
    """`GET /admin/system` (docs/58 §3.2, ADR-116, ADR-130, ADR-139) -
    liveness of DB/Redis plus today's activity counts, not telemetry.
    `database`/`redis` are `"ok"`/`"down"`, never an exception - a
    dependency being unreachable must render as `"down"` in a 200
    response, not a 500. `news`/`economic_calendar` are similarly
    fail-open (ADR-139) - a Redis outage renders as `None` fields, never
    a 500."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "database": "ok",
                "redis": "ok",
                "signals_today": 4,
                "ai_analyses_today": 9,
                "news": {
                    "providers": ["mock"],
                    "uses_mock": True,
                    "last_success_at": "2026-08-07T09:00:00Z",
                    "last_error": None,
                },
                "economic_calendar": {
                    "providers": ["mock"],
                    "uses_mock": True,
                    "last_success_at": "2026-08-07T09:00:00Z",
                    "last_error": None,
                },
            }
        }
    )

    database: Literal["ok", "down"]
    redis: Literal["ok", "down"]
    signals_today: int
    ai_analyses_today: int
    news: IngestionHealthResponse
    economic_calendar: IngestionHealthResponse


class AdminAnalyticsResponse(BaseModel):
    """`GET /admin/analytics` (docs/58 §3.2, ADR-130) - exactly the two
    figures docs/58 specifies; docs/25 §15's longer wishlist (most viewed
    assets, confidence distribution, average AI response time) is
    deferred - no view-tracking or latency-recording infrastructure
    exists to source those from."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "daily_active_users": 3,
                "signal_type_distribution": {"buy": 5, "sell": 2},
            }
        }
    )

    daily_active_users: int
    signal_type_distribution: dict[str, int]


class MaintenanceActionRequest(BaseModel):
    """`POST /admin/maintenance` (docs/58 §3.2, ADR-117) - `Literal`, not a
    free string with an `if` chain, so an unknown action is rejected by
    schema validation (422) before it ever reaches the service layer."""

    action: Literal["refresh_news", "refresh_calendar"]


class NewsRefreshResponse(BaseModel):
    articles_ingested: int = Field(examples=[3])


class CalendarRefreshResponse(BaseModel):
    events_created: int = Field(examples=[2])
    events_updated: int = Field(examples=[1])


class MaintenanceActionResponse(BaseModel):
    """Shared response shape for both maintenance actions - only the
    field matching `action` is populated, the other is `null`, since news
    and calendar refreshes return different counts (docs/58 §3.2)."""

    action: Literal["refresh_news", "refresh_calendar"]
    news: NewsRefreshResponse | None = None
    calendar: CalendarRefreshResponse | None = None

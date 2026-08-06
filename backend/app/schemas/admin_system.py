from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AdminSystemStatusResponse(BaseModel):
    """`GET /admin/system` (docs/58 §3.2, ADR-116, ADR-130) - liveness of
    DB/Redis plus today's activity counts, not telemetry. `database`/
    `redis` are `"ok"`/`"down"`, never an exception - a dependency being
    unreachable must render as `"down"` in a 200 response, not a 500."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "database": "ok",
                "redis": "ok",
                "signals_today": 4,
                "ai_analyses_today": 9,
            }
        }
    )

    database: Literal["ok", "down"]
    redis: Literal["ok", "down"]
    signals_today: int
    ai_analyses_today: int


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

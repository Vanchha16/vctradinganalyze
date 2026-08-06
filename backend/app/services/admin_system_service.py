import uuid
from datetime import UTC, datetime
from typing import Literal

import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit_log import AuditLog
from app.models.enums import SignalStatus
from app.models.signal import Signal
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.schemas.admin_system import AdminAnalyticsResponse, AdminSystemStatusResponse
from app.services.economic_calendar_ingestion_pipeline import (
    EconomicCalendarIngestionPipeline,
    default_window,
)
from app.services.news_ingestion_pipeline import NewsIngestionPipeline, default_since


class AdminSystemService:
    """Business logic for the five non-user Admin endpoints (docs/58
    §3.2, Phase 7D-C, ADR-130) - `GET /admin/{signals,system,analytics}`,
    `POST /admin/{news,maintenance}`. Mirrors `AdminUserService`'s shape:
    constructor-injected repositories/pipelines, one public method per
    use case, a private `_audit` helper for the two mutating actions.

    `refresh_news`/`refresh_calendar` are the single shared
    implementation `POST /admin/news` and `POST /admin/maintenance` both
    call (docs/58 deliberately specifies both, see ADR-130) - each
    audits and returns from exactly one place, never duplicated per
    route.
    """

    def __init__(
        self,
        db: Session,
        signal_repository: SignalRepository,
        ai_analysis_repository: AIAnalysisRepository,
        user_session_repository: UserSessionRepository,
        audit_log_repository: AuditLogRepository,
        news_pipeline: NewsIngestionPipeline,
        calendar_pipeline: EconomicCalendarIngestionPipeline,
    ) -> None:
        self._db = db
        self._signal_repository = signal_repository
        self._ai_analysis_repository = ai_analysis_repository
        self._user_session_repository = user_session_repository
        self._audit_log_repository = audit_log_repository
        self._news_pipeline = news_pipeline
        self._calendar_pipeline = calendar_pipeline

    # --- Reads ---------------------------------------------------------

    def list_signals(
        self,
        *,
        asset_id: uuid.UUID | None = None,
        status: SignalStatus | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Signal], int]:
        """docs/58 §3.2 describes this as "all users, not just caller's" -
        but `Signal` has no `user_id` column at all (see ADR-130): every
        signal is asset-level, and the existing `GET /signals` route is
        already unscoped for any authenticated caller. This method is
        therefore identical in scope to what the public route already
        returns - the admin surface exists for a consistent `/admin/*`
        dashboard entry point, not to unlock previously-hidden rows."""
        offset = (page - 1) * limit
        items = list(
            self._signal_repository.find_paginated(
                asset_id=asset_id, status=status, offset=offset, limit=limit
            )
        )
        total = self._signal_repository.count_filtered(asset_id=asset_id, status=status)
        return items, total

    def get_system_status(self) -> AdminSystemStatusResponse:
        """`GET /admin/system` (ADR-116) - liveness + today's counts, not
        telemetry. Must never 500: each dependency check is isolated so a
        Redis outage still renders `redis: "down"` in a 200 response."""
        database_status: Literal["ok", "down"] = "ok"
        try:
            self._db.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 - liveness probe, any failure means "down"
            database_status = "down"

        redis_status: Literal["ok", "down"] = "ok"
        try:
            redis_client = redis.Redis.from_url(settings.redis_url)
            redis_client.ping()
        except Exception:  # noqa: BLE001 - same as above
            redis_status = "down"

        since_midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return AdminSystemStatusResponse(
            database=database_status,
            redis=redis_status,
            signals_today=self._signal_repository.count_since(since_midnight),
            ai_analyses_today=self._ai_analysis_repository.count_since(since_midnight),
        )

    def get_analytics(self) -> AdminAnalyticsResponse:
        """`GET /admin/analytics` (docs/58 §3.2) - exactly the two figures
        specified. Empty-data case (no sessions, no signals) is just a 0
        count / empty dict, not a special case to guard."""
        since_midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_active_users = self._user_session_repository.count_distinct_users_since(
            since_midnight
        )
        distribution = self._signal_repository.count_by_signal_type()
        return AdminAnalyticsResponse(
            daily_active_users=daily_active_users,
            signal_type_distribution={
                signal_type.value: count for signal_type, count in distribution.items()
            },
        )

    # --- Mutations -------------------------------------------------------

    def refresh_news(self, actor: User, *, ip_address: str | None = None) -> int:
        """Shared implementation for `POST /admin/news` and
        `POST /admin/maintenance {"action": "refresh_news"}` - calls the
        exact same `NewsIngestionPipeline` the `news_sentiment.ingest`
        Celery task uses (docs/58 §3.2), just admin-invoked. Runs inline
        (blocking) per docs/58's approved spec - see ADR-130 for the
        synchronous-ingestion tradeoff this accepts."""
        since = default_since(settings.news_lookback_hours)
        articles_ingested = self._news_pipeline.run(since)

        self._audit(
            actor.id,
            action="admin_news_refreshed",
            resource="news_articles",
            ip_address=ip_address,
            context={"articles_ingested": articles_ingested},
        )
        self._commit()
        return articles_ingested

    def refresh_calendar(self, actor: User, *, ip_address: str | None = None) -> tuple[int, int]:
        """Shared implementation for
        `POST /admin/maintenance {"action": "refresh_calendar"}` - calls
        the exact same `EconomicCalendarIngestionPipeline` the
        `economic_calendar.ingest` Celery task uses."""
        start, end = default_window(
            settings.economic_calendar_lookback_days, settings.economic_calendar_lookahead_days
        )
        created, updated = self._calendar_pipeline.run(start, end)

        self._audit(
            actor.id,
            action="admin_calendar_refreshed",
            resource="economic_events",
            ip_address=ip_address,
            context={"events_created": created, "events_updated": updated},
        )
        self._commit()
        return created, updated

    # --- Internal helpers --------------------------------------------------

    def _audit(
        self,
        user_id: uuid.UUID,
        *,
        action: str,
        resource: str,
        ip_address: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        self._audit_log_repository.create(
            AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                ip_address=ip_address,
                context=context,
            )
        )

    def _commit(self) -> None:
        self._audit_log_repository.commit()

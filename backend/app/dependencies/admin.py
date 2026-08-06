from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.economic_calendar import get_economic_calendar_providers
from app.dependencies.news import get_news_providers
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.economic_event_repository import EconomicEventRepository
from app.repositories.news_article_repository import NewsArticleRepository
from app.repositories.news_sentiment_repository import NewsSentimentRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.admin_audit_log_service import AdminAuditLogService
from app.services.admin_system_service import AdminSystemService
from app.services.admin_user_service import AdminUserService
from app.services.economic_calendar_ingestion_pipeline import EconomicCalendarIngestionPipeline
from app.services.news_ingestion_pipeline import NewsIngestionPipeline
from app.services.news_sentiment.ai_summary_generator import AISummaryGenerator
from app.services.user_service import UserService


def get_admin_user_service(db: Annotated[Session, Depends(get_db)]) -> AdminUserService:
    user_repository = UserRepository(db)
    return AdminUserService(
        user_repository=user_repository,
        user_session_repository=UserSessionRepository(db),
        audit_log_repository=AuditLogRepository(db),
        user_service=UserService(user_repository),
    )


def get_admin_audit_log_service(db: Annotated[Session, Depends(get_db)]) -> AdminAuditLogService:
    return AdminAuditLogService(
        audit_log_repository=AuditLogRepository(db), user_repository=UserRepository(db)
    )


def get_admin_system_service(db: Annotated[Session, Depends(get_db)]) -> AdminSystemService:
    """Composes `AdminSystemService` (docs/58 §3.2, Phase 7D-C) - the two
    ingestion pipelines are built exactly as `news_sentiment_tasks.
    ingest_news_task`/`economic_calendar_tasks.ingest_economic_calendar_
    task` already build them, so `POST /admin/news`/`/admin/maintenance`
    call the identical pipeline the Celery beat schedule uses."""
    news_pipeline = NewsIngestionPipeline(
        providers=get_news_providers(),
        source_repository=NewsSourceRepository(db),
        article_repository=NewsArticleRepository(db),
        sentiment_repository=NewsSentimentRepository(db),
        asset_repository=AssetRepository(db),
        ai_summary_generator=AISummaryGenerator(),
    )
    calendar_pipeline = EconomicCalendarIngestionPipeline(
        providers=get_economic_calendar_providers(),
        event_repository=EconomicEventRepository(db),
    )
    return AdminSystemService(
        db=db,
        signal_repository=SignalRepository(db),
        ai_analysis_repository=AIAnalysisRepository(db),
        user_session_repository=UserSessionRepository(db),
        audit_log_repository=AuditLogRepository(db),
        news_pipeline=news_pipeline,
        calendar_pipeline=calendar_pipeline,
    )

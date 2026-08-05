from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.admin_user_service import AdminUserService
from app.services.user_service import UserService


def get_admin_user_service(db: Annotated[Session, Depends(get_db)]) -> AdminUserService:
    user_repository = UserRepository(db)
    return AdminUserService(
        user_repository=user_repository,
        user_session_repository=UserSessionRepository(db),
        audit_log_repository=AuditLogRepository(db),
        user_service=UserService(user_repository),
    )

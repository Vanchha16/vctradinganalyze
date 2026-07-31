import uuid
from collections.abc import Sequence

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> Sequence[AuditLog]:
        query = self._filter_by(self._query(), user_id=user_id)
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def create(self, log: AuditLog) -> AuditLog:
        self.session.add(log)
        self.session.flush()
        return log

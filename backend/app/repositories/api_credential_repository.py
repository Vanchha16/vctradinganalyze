from collections.abc import Sequence

from sqlalchemy import select

from app.models.api_credential import ApiCredential
from app.repositories.base import BaseRepository


class ApiCredentialRepository(BaseRepository[ApiCredential]):
    model = ApiCredential

    def create(self, credential: ApiCredential) -> ApiCredential:
        """`BaseRepository` deliberately stops short of CRUD, so each
        repository declares the writes it actually needs - same shape as
        `AuditLogRepository.create`."""
        self.session.add(credential)
        self.session.flush()
        return credential

    def delete(self, credential: ApiCredential) -> None:
        self.session.delete(credential)
        self.session.flush()

    def get_by_name(self, name: str) -> ApiCredential | None:
        return self.session.execute(
            select(ApiCredential).where(ApiCredential.name == name)
        ).scalar_one_or_none()

    def list_all(self) -> Sequence[ApiCredential]:
        return (
            self.session.execute(select(ApiCredential).order_by(ApiCredential.name)).scalars().all()
        )

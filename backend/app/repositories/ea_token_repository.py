import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.ea_token import EaToken
from app.repositories.base import BaseRepository


class EaTokenRepository(BaseRepository[EaToken]):
    model = EaToken

    def create(self, token: EaToken) -> EaToken:
        self.session.add(token)
        self.session.flush()
        return token

    def delete(self, token: EaToken) -> None:
        self.session.delete(token)
        self.session.flush()

    def get_by_id(self, token_id: uuid.UUID) -> EaToken | None:
        return self.session.get(EaToken, token_id)

    def get_by_hash(self, token_hash: str) -> EaToken | None:
        return self.session.execute(
            select(EaToken).where(EaToken.token_hash == token_hash)
        ).scalar_one_or_none()

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[EaToken]:
        return (
            self.session.execute(
                select(EaToken).where(EaToken.user_id == user_id).order_by(EaToken.created_at)
            )
            .scalars()
            .all()
        )

    def count_for_user(self, user_id: uuid.UUID) -> int:
        return self.session.execute(
            select(func.count()).select_from(EaToken).where(EaToken.user_id == user_id)
        ).scalar_one()

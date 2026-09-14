import uuid

from sqlalchemy import select

from app.models.enums import UserRole
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.repositories.base import BaseRepository


class TelegramAccountRepository(BaseRepository[TelegramAccount]):
    model = TelegramAccount

    def create(self, account: TelegramAccount) -> TelegramAccount:
        self.session.add(account)
        self.session.flush()
        return account

    def get_by_user_id(self, user_id: uuid.UUID) -> TelegramAccount | None:
        query = self._query().filter_by(user_id=user_id)
        return self.session.execute(query).scalar_one_or_none()

    def get_by_link_code(self, link_code: str) -> TelegramAccount | None:
        query = self._query().filter_by(link_code=link_code)
        return self.session.execute(query).scalar_one_or_none()

    def get_by_chat_id(self, chat_id: str) -> TelegramAccount | None:
        """Looks up the linked account behind an inbound chat message
        (§13's menu buttons/chart-symbol replies) - the reverse direction
        of `get_by_user_id`, keyed by the Telegram side of the link."""
        query = self._query().filter_by(telegram_chat_id=chat_id)
        return self.session.execute(query).scalar_one_or_none()

    def list_linked(self) -> list[TelegramAccount]:
        query = self._query().filter(TelegramAccount.linked_at.is_not(None))
        return list(self.session.execute(query).scalars().all())

    def list_linked_for_role(self, role: UserRole) -> list[TelegramAccount]:
        """Linked accounts of active, not-deleted users holding `role` -
        ADR-170's EA alerts go to super admins only, not to every subscriber."""
        query = (
            select(TelegramAccount)
            .join(User, User.id == TelegramAccount.user_id)
            .where(
                TelegramAccount.linked_at.is_not(None),
                User.role == role,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        return list(self.session.execute(query).scalars().all())

    def delete(self, account: TelegramAccount) -> None:
        self.session.delete(account)
        self.session.flush()

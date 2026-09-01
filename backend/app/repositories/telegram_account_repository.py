import uuid

from app.models.telegram_account import TelegramAccount
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

    def delete(self, account: TelegramAccount) -> None:
        self.session.delete(account)
        self.session.flush()

from app.models.oauth_account import OAuthAccount
from app.repositories.base import BaseRepository


class OAuthAccountRepository(BaseRepository[OAuthAccount]):
    model = OAuthAccount

    def get_by_provider_account(self, provider: str, provider_user_id: str) -> OAuthAccount | None:
        query = self._filter_by(self._query(), provider=provider, provider_user_id=provider_user_id)
        return self.session.execute(query).scalar_one_or_none()

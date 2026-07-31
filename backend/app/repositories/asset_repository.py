from collections.abc import Sequence

from app.models.asset import Asset
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    def get_by_symbol(self, symbol: str) -> Asset | None:
        query = self._filter_by(self._query(), symbol=symbol)
        return self.session.execute(query).scalar_one_or_none()

    def list_active(self, *, offset: int = 0, limit: int = 20) -> Sequence[Asset]:
        query = self._filter_by(self._query(), is_active=True)
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        self.session.flush()
        return asset

from collections.abc import Sequence
from typing import Any

from app.models.asset import Asset
from app.models.enums import MarketType
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

    def list_filtered(
        self,
        *,
        market_type: MarketType | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Asset]:
        query = self._filter_by(self._query(), **self._build_filters(market_type, is_active))
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def count_filtered(
        self, *, market_type: MarketType | None = None, is_active: bool | None = None
    ) -> int:
        query = self._filter_by(self._query(), **self._build_filters(market_type, is_active))
        return self._count(query)

    @staticmethod
    def _build_filters(market_type: MarketType | None, is_active: bool | None) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if market_type is not None:
            filters["market_type"] = market_type
        if is_active is not None:
            filters["is_active"] = is_active
        return filters

    def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        self.session.flush()
        return asset

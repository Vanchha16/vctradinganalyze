import uuid
from collections.abc import Sequence

from sqlalchemy import Select, or_

from app.models.asset import Asset
from app.models.enums import MarketType
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    def get_by_id(self, asset_id: uuid.UUID) -> Asset | None:
        return self.session.get(Asset, asset_id)

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
        search: str | None = None,
        market_type: MarketType | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Asset]:
        """`search` (Phase 9F, `AdminAssetService`) is additive - every
        existing caller omits it and gets the prior unfiltered behavior,
        same convention `SignalRepository.find_paginated`'s `timeframe`
        addition already established."""
        query = self._apply_filters(self._query(), search, market_type, is_active)
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

    def count_filtered(
        self,
        *,
        search: str | None = None,
        market_type: MarketType | None = None,
        is_active: bool | None = None,
    ) -> int:
        query = self._apply_filters(self._query(), search, market_type, is_active)
        return self._count(query)

    @staticmethod
    def _apply_filters(
        query: Select[tuple[Asset]],
        search: str | None,
        market_type: MarketType | None,
        is_active: bool | None,
    ) -> Select[tuple[Asset]]:
        if search:
            pattern = f"%{search}%"
            query = query.where(or_(Asset.symbol.ilike(pattern), Asset.name.ilike(pattern)))
        if market_type is not None:
            query = query.where(Asset.market_type == market_type)
        if is_active is not None:
            query = query.where(Asset.is_active == is_active)
        return query

    def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        self.session.flush()
        return asset

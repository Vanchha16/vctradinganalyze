import uuid
from collections.abc import Sequence

from app.exceptions import ConflictException, ResourceNotFoundException
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.repositories.asset_repository import AssetRepository
from app.repositories.watchlist_repository import WatchlistRepository


class WatchlistService:
    """Business rules for Watchlists (docs/58 §2.2, ADR-114/ADR-128).

    Mirrors `AdminUserService`'s shape: constructor-injected repositories,
    one public method per use case, a private `_resolve_owned` guard. Every
    operation is scoped to the calling user - a watchlist that exists but
    belongs to someone else is treated identically to one that doesn't
    exist at all, so ownership can never be probed from the outside."""

    def __init__(
        self, watchlist_repository: WatchlistRepository, asset_repository: AssetRepository
    ) -> None:
        self._watchlist_repository = watchlist_repository
        self._asset_repository = asset_repository

    # --- Watchlists ------------------------------------------------------

    def list_watchlists(self, user_id: uuid.UUID) -> list[tuple[Watchlist, int]]:
        watchlists = self._watchlist_repository.list_for_user(user_id)
        return [
            (watchlist, self._watchlist_repository.count_items(watchlist.id))
            for watchlist in watchlists
        ]

    def get_watchlist_detail(
        self, user_id: uuid.UUID, watchlist_id: uuid.UUID
    ) -> tuple[Watchlist, Sequence[WatchlistItem]]:
        watchlist = self._resolve_owned(user_id, watchlist_id)
        items = self._watchlist_repository.list_items(watchlist.id)
        return watchlist, items

    def create_watchlist(self, user_id: uuid.UUID, name: str) -> Watchlist:
        watchlist = Watchlist(user_id=user_id, name=name)
        self._watchlist_repository.create(watchlist)
        self._watchlist_repository.commit()
        return watchlist

    def rename_watchlist(self, user_id: uuid.UUID, watchlist_id: uuid.UUID, name: str) -> Watchlist:
        watchlist = self._resolve_owned(user_id, watchlist_id)
        watchlist.name = name
        self._watchlist_repository.commit()
        return watchlist

    def count_items(self, watchlist_id: uuid.UUID) -> int:
        return self._watchlist_repository.count_items(watchlist_id)

    def delete_watchlist(self, user_id: uuid.UUID, watchlist_id: uuid.UUID) -> None:
        watchlist = self._resolve_owned(user_id, watchlist_id)
        self._watchlist_repository.delete(watchlist)
        self._watchlist_repository.commit()

    # --- Watchlist items ---------------------------------------------------

    def add_asset(
        self, user_id: uuid.UUID, watchlist_id: uuid.UUID, asset_id: uuid.UUID
    ) -> WatchlistItem:
        watchlist = self._resolve_owned(user_id, watchlist_id)

        if self._asset_repository.get_by_id(asset_id) is None:
            raise ResourceNotFoundException(f"Unknown asset id: {asset_id}")

        if self._watchlist_repository.get_item(watchlist.id, asset_id) is not None:
            raise ConflictException("Asset is already in this watchlist.")

        item = WatchlistItem(watchlist_id=watchlist.id, asset_id=asset_id)
        self._watchlist_repository.add_item(item)
        self._watchlist_repository.commit()
        return item

    def remove_asset(
        self, user_id: uuid.UUID, watchlist_id: uuid.UUID, asset_id: uuid.UUID
    ) -> None:
        watchlist = self._resolve_owned(user_id, watchlist_id)

        item = self._watchlist_repository.get_item(watchlist.id, asset_id)
        if item is None:
            raise ResourceNotFoundException(f"Asset {asset_id} is not in this watchlist.")

        self._watchlist_repository.remove_item(item)
        self._watchlist_repository.commit()

    # --- Internal helpers --------------------------------------------------

    def _resolve_owned(self, user_id: uuid.UUID, watchlist_id: uuid.UUID) -> Watchlist:
        watchlist = self._watchlist_repository.get_by_id(watchlist_id)
        if watchlist is None or watchlist.user_id != user_id:
            raise ResourceNotFoundException(f"Unknown watchlist id: {watchlist_id}")
        return watchlist

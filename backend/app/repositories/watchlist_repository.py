import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.repositories.base import BaseRepository


class WatchlistRepository(BaseRepository[Watchlist]):
    """Persistence for `Watchlist` + `WatchlistItem` together (docs/58
    §2.2) - a `WatchlistItem` never has meaning without its parent
    `Watchlist`, and every route that touches items always already has the
    watchlist in hand, so one repository covers both tables rather than
    splitting them the way `Signal`/`SignalBookmark` are split (those two
    are independently addressable elsewhere in the API)."""

    model = Watchlist

    # --- Watchlists ------------------------------------------------------

    def create(self, watchlist: Watchlist) -> Watchlist:
        self.session.add(watchlist)
        self.session.flush()
        return watchlist

    def get_by_id(self, watchlist_id: uuid.UUID) -> Watchlist | None:
        return self.session.get(Watchlist, watchlist_id)

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[Watchlist]:
        query = self._query().filter_by(user_id=user_id).order_by(Watchlist.created_at.desc())
        return self.session.execute(query).scalars().all()

    def delete(self, watchlist: Watchlist) -> None:
        self.session.delete(watchlist)
        self.session.flush()

    # --- Watchlist items ---------------------------------------------------

    def count_items(self, watchlist_id: uuid.UUID) -> int:
        # `BaseRepository._count` is typed against `self.model` (`Watchlist`
        # here) - this counts the *other* table this repository manages,
        # so it's a plain inline count rather than misusing that helper.
        query = select(func.count()).select_from(WatchlistItem).filter_by(watchlist_id=watchlist_id)
        return self.session.execute(query).scalar_one()

    def list_items(self, watchlist_id: uuid.UUID) -> Sequence[WatchlistItem]:
        query = (
            select(WatchlistItem)
            .filter_by(watchlist_id=watchlist_id)
            .order_by(WatchlistItem.created_at.asc())
        )
        return self.session.execute(query).scalars().all()

    def get_item(self, watchlist_id: uuid.UUID, asset_id: uuid.UUID) -> WatchlistItem | None:
        query = select(WatchlistItem).filter_by(watchlist_id=watchlist_id, asset_id=asset_id)
        return self.session.execute(query).scalar_one_or_none()

    def add_item(self, item: WatchlistItem) -> WatchlistItem:
        self.session.add(item)
        self.session.flush()
        return item

    def remove_item(self, item: WatchlistItem) -> None:
        self.session.delete(item)
        self.session.flush()

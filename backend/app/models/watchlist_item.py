import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin


class WatchlistItem(Base, UUIDMixin, CreatedAtMixin):
    """An asset's membership in a `Watchlist` (docs/03 §12, docs/58 §2.1).

    Append-only: an item is either present or absent, never updated in
    place - mirrors `SignalBookmark`'s shape exactly, including the
    inferred `(watchlist_id, asset_id)` uniqueness precedent
    (ADR-022/ADR-090, recorded for this table in ADR-128)."""

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "asset_id", name="uq_watchlist_items_watchlist_asset"),
    )

    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("watchlists.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )

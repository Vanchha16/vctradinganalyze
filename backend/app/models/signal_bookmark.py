import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin


class SignalBookmark(Base, UUIDMixin, CreatedAtMixin):
    """A user's bookmark of a `Signal` (docs/51 §8, ADR-090) - inferred,
    not specified in docs/03, following `OAuthAccount`'s
    `(provider, provider_user_id)` uniqueness precedent (ADR-022).
    Append-only: a bookmark is either present or absent, never updated
    in place.
    """

    __tablename__ = "signal_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "signal_id", name="uq_signal_bookmarks_user_signal"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("signals.id", ondelete="CASCADE"), index=True, nullable=False
    )

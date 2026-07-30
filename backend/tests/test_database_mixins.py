import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class _Widget(Base, UUIDMixin, TimestampMixin):
    """Test-only model used to exercise the mixins in isolation.

    SQLite (used here for a fast, dependency-free unit test) returns naive
    datetimes from CURRENT_TIMESTAMP regardless of DateTime(timezone=True);
    tz-awareness of created_at/updated_at is guaranteed by Postgres in
    production, not by this mixin, so it isn't asserted here.
    """

    __tablename__ = "test_widgets"

    name: Mapped[str] = mapped_column()


def test_uuid_and_timestamp_mixins_populate_on_insert() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[_Widget.__table__])

    with Session(engine) as session:
        widget = _Widget(name="test")
        session.add(widget)
        session.commit()
        session.refresh(widget)

        assert isinstance(widget.id, uuid.UUID)
        assert widget.created_at is not None
        assert widget.updated_at is not None

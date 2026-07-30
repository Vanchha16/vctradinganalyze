import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database.base import Base
from app.database.mixins import UUIDMixin
from app.repositories.base import BaseRepository


class _Item(Base, UUIDMixin):
    __tablename__ = "test_items"

    name: Mapped[str] = mapped_column()


class _ItemRepository(BaseRepository[_Item]):
    model = _Item


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[_Item.__table__])
    with Session(engine) as session:
        yield session


def test_query_and_filter_by(session: Session) -> None:
    session.add_all([_Item(name="a"), _Item(name="b")])
    session.commit()

    repo = _ItemRepository(session)
    query = repo._filter_by(repo._query(), name="a")
    results = session.execute(query).scalars().all()

    assert [item.name for item in results] == ["a"]


def test_paginate_and_count(session: Session) -> None:
    session.add_all([_Item(name=f"item-{i}") for i in range(5)])
    session.commit()

    repo = _ItemRepository(session)
    query = repo._query()

    assert repo._count(query) == 5

    page = session.execute(repo._paginate(query, offset=2, limit=2)).scalars().all()
    assert len(page) == 2


def test_transaction_commits_on_success(session: Session) -> None:
    repo = _ItemRepository(session)

    with repo.transaction():
        session.add(_Item(name="committed"))

    session.rollback()  # no-op if the transaction already committed
    assert repo._count(repo._query()) == 1


def test_transaction_rolls_back_on_failure(session: Session) -> None:
    repo = _ItemRepository(session)

    with pytest.raises(ValueError):
        with repo.transaction():
            session.add(_Item(name="doomed"))
            raise ValueError("boom")

    assert repo._count(repo._query()) == 0

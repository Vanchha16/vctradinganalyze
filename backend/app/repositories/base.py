from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.database.base import Base


class BaseRepository[ModelType: Base]:
    """Shared repository foundation.

    Provides session access, query building, pagination, and transaction
    helpers common to all repositories. Concrete repositories define the
    actual data-access operations for their model - this class deliberately
    stops short of CRUD so it never presumes how a given model should be
    queried or mutated.
    """

    model: type[ModelType]

    def __init__(self, session: Session) -> None:
        self.session = session

    def _query(self) -> Select[tuple[ModelType]]:
        return select(self.model)

    def _filter_by(
        self, query: Select[tuple[ModelType]], **filters: Any
    ) -> Select[tuple[ModelType]]:
        return query.filter_by(**filters)

    def _paginate(
        self, query: Select[tuple[ModelType]], *, offset: int = 0, limit: int = 20
    ) -> Select[tuple[ModelType]]:
        return query.offset(offset).limit(limit)

    def _count(self, query: Select[tuple[ModelType]]) -> int:
        count_query = select(func.count()).select_from(query.subquery())
        return self.session.execute(count_query).scalar_one()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Commit on success, roll back automatically on failure."""
        try:
            yield
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def refresh(self, instance: ModelType) -> None:
        self.session.refresh(instance)

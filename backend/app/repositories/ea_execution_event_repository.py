import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import Select, select

from app.models.ea_execution_event import EaExecutionEvent
from app.repositories.base import BaseRepository


class EaExecutionEventRepository(BaseRepository[EaExecutionEvent]):
    model = EaExecutionEvent

    def add_all(self, events: Sequence[EaExecutionEvent]) -> None:
        self.session.add_all(events)
        self.session.flush()

    def existing_keys(self, user_id: uuid.UUID, keys: Collection[str]) -> set[str]:
        if not keys:
            return set()
        query = select(EaExecutionEvent.event_key).where(
            EaExecutionEvent.user_id == user_id, EaExecutionEvent.event_key.in_(keys)
        )
        return set(self.session.execute(query).scalars().all())

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        signal_id: uuid.UUID | None = None,
        dry_run: bool | None = None,
        event_type: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[EaExecutionEvent]:
        """Newest first by when it happened, then by arrival - two events
        from one poll share a second, and arrival order is the order the EA
        queued them."""
        query = self._filtered(
            user_id, signal_id=signal_id, dry_run=dry_run, event_type=event_type
        ).order_by(EaExecutionEvent.occurred_at.desc(), EaExecutionEvent.created_at.desc())
        paginated = self._paginate(query, offset=offset, limit=limit)
        return self.session.execute(paginated).scalars().all()

    def count_for_user(
        self,
        user_id: uuid.UUID,
        *,
        signal_id: uuid.UUID | None = None,
        dry_run: bool | None = None,
        event_type: str | None = None,
    ) -> int:
        return self._count(
            self._filtered(user_id, signal_id=signal_id, dry_run=dry_run, event_type=event_type)
        )

    def _filtered(
        self,
        user_id: uuid.UUID,
        *,
        signal_id: uuid.UUID | None,
        dry_run: bool | None,
        event_type: str | None,
    ) -> Select[tuple[EaExecutionEvent]]:
        query = self._query().where(EaExecutionEvent.user_id == user_id)
        if signal_id is not None:
            query = query.where(EaExecutionEvent.signal_id == signal_id)
        if dry_run is not None:
            query = query.where(EaExecutionEvent.dry_run == dry_run)
        if event_type is not None:
            query = query.where(EaExecutionEvent.event_type == event_type)
        return query

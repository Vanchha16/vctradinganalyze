import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from app.models.enums import SMCEventStatus, SMCEventType, Timeframe
from app.models.smc_event import SMCEvent
from app.repositories.base import BaseRepository


class SMCEventRepository(BaseRepository[SMCEvent]):
    model = SMCEvent

    def create(self, event: SMCEvent) -> SMCEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def get_by_id(self, event_id: uuid.UUID) -> SMCEvent | None:
        return self.session.get(SMCEvent, event_id)

    def get_by_natural_key(
        self,
        asset_id: uuid.UUID,
        timeframe: Timeframe,
        event_type: SMCEventType,
        detected_at: datetime,
    ) -> SMCEvent | None:
        """A zone's (asset, timeframe, event_type, detected_at) is stable
        across repeated `analyze()` calls, since detection is
        deterministic - used to update an existing row's lifecycle state
        in place instead of inserting a duplicate (ADR-033)."""
        query = self._filter_by(
            self._query(),
            asset_id=asset_id,
            timeframe=timeframe,
            event_type=event_type,
            detected_at=detected_at,
        )
        return self.session.execute(query).scalar_one_or_none()

    def get_latest_detected_at(self, asset_id: uuid.UUID, timeframe: Timeframe) -> datetime | None:
        query = (
            self._filter_by(self._query(), asset_id=asset_id, timeframe=timeframe)
            .order_by(SMCEvent.detected_at.desc())
            .limit(1)
        )
        event = self.session.execute(query).scalar_one_or_none()
        return event.detected_at if event is not None else None

    def list_active(
        self,
        asset_id: uuid.UUID,
        timeframe: Timeframe,
        *,
        event_type: SMCEventType | None = None,
    ) -> Sequence[SMCEvent]:
        filters: dict[str, object] = {
            "asset_id": asset_id,
            "timeframe": timeframe,
            "status": SMCEventStatus.ACTIVE,
        }
        if event_type is not None:
            filters["event_type"] = event_type
        query = self._filter_by(self._query(), **filters).order_by(SMCEvent.detected_at.asc())
        return self.session.execute(query).scalars().all()

    def list_for_asset_timeframe(
        self,
        asset_id: uuid.UUID,
        timeframe: Timeframe,
        *,
        event_type: SMCEventType | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> Sequence[SMCEvent]:
        query = select(SMCEvent).where(
            SMCEvent.asset_id == asset_id, SMCEvent.timeframe == timeframe
        )
        if event_type is not None:
            query = query.where(SMCEvent.event_type == event_type)
        if not include_archived:
            query = query.where(SMCEvent.status != SMCEventStatus.ARCHIVED)
        query = query.order_by(SMCEvent.detected_at.desc()).limit(limit)
        return self.session.execute(query).scalars().all()

    def update_status(self, event: SMCEvent, status: SMCEventStatus) -> SMCEvent:
        """Transition an existing event's lifecycle state in place
        (ADR-033/ADR-037) - `smc_events` rows are mutable, unlike every
        other append-only table in this project. The row is never
        deleted, only its `status` (and typically `context`) change."""
        event.status = status
        self.session.flush()
        return event

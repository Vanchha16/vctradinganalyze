import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.enums import SignalStatus
from app.models.signal import Signal
from app.repositories.base import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    model = Signal

    def create(self, signal: Signal) -> Signal:
        self.session.add(signal)
        self.session.flush()
        return signal

    def get_by_id(self, signal_id: uuid.UUID) -> Signal | None:
        return self.session.get(Signal, signal_id)

    def find_paginated(
        self,
        *,
        asset_id: uuid.UUID | None = None,
        status: SignalStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Signal]:
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if status is not None:
            query = query.where(Signal.status == status)
        query = query.order_by(Signal.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(
        self, *, asset_id: uuid.UUID | None = None, status: SignalStatus | None = None
    ) -> int:
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if status is not None:
            query = query.where(Signal.status == status)
        return self._count(query)

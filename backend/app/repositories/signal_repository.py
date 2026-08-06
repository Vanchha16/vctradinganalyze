import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from app.models.enums import SignalStatus, SignalType, Timeframe
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
        timeframe: Timeframe | None = None,
        status: SignalStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Signal]:
        """`timeframe` (docs/52 §2, added for AI Chat's "latest signal for
        this asset/timeframe" grounding lookup) is additive - every
        existing caller omits it and gets the prior unfiltered behavior."""
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(Signal.timeframe == timeframe)
        if status is not None:
            query = query.where(Signal.status == status)
        query = query.order_by(Signal.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(
        self,
        *,
        asset_id: uuid.UUID | None = None,
        timeframe: Timeframe | None = None,
        status: SignalStatus | None = None,
    ) -> int:
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(Signal.timeframe == timeframe)
        if status is not None:
            query = query.where(Signal.status == status)
        return self._count(query)

    def count_since(self, since: datetime) -> int:
        """Today's "signals generated" count (docs/58 §3.2, `GET
        /admin/system`)."""
        query = select(func.count()).select_from(Signal).where(Signal.created_at >= since)
        return self.session.execute(query).scalar_one()

    def count_by_signal_type(self) -> dict[SignalType, int]:
        """"Recommendation distribution" (docs/58 §3.2, `GET
        /admin/analytics`) - `signals` has no `recommendation` column
        (that field lives on `ai_analysis`); `signal_type` (BUY/SELL) is
        the closest actual field on this table and the only one a
        distribution grouped "on signals" can mean, since a `Signal` row
        only ever exists for a BUY/SELL outcome in the first place
        (ADR-086 - WAIT produces no `Signal` row to count). Recorded as an
        inferred reading of docs/58's wording, not a literal match, in
        ADR-130."""
        query = select(Signal.signal_type, func.count()).group_by(Signal.signal_type)
        return {signal_type: count for signal_type, count in self.session.execute(query)}

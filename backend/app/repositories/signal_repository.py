import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

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

    def find_open_for_asset(
        self, asset_id: uuid.UUID, *, created_since: datetime
    ) -> Sequence[Signal]:
        """Stored ACTIVE/TRIGGERED signals for one asset, newest first -
        the MT5 EA feed's candidates (ADR-161). Stored status only: the
        caller still applies `status_resolver.effective_status`, since an
        ACTIVE row can already be EXPIRED at read time (ADR-088)."""
        query = (
            select(Signal)
            .where(
                Signal.asset_id == asset_id,
                Signal.status.in_([SignalStatus.ACTIVE, SignalStatus.TRIGGERED]),
                Signal.created_at >= created_since,
            )
            .order_by(Signal.created_at.desc())
        )
        return self.session.execute(query).scalars().all()

    def count_since(self, since: datetime) -> int:
        """Today's "signals generated" count (docs/58 §3.2, `GET
        /admin/system`)."""
        query = select(func.count()).select_from(Signal).where(Signal.created_at >= since)
        return self.session.execute(query).scalar_one()

    def count_by_status_since(self, since: datetime) -> dict[SignalStatus, int]:
        """Per-status breakdown for the Telegram bot's Summary Report
        button (§13) - one query per reporting window (today/last 7
        days), same grouping style as `count_by_signal_type`."""
        query = (
            select(Signal.status, func.count())
            .where(Signal.created_at >= since)
            .group_by(Signal.status)
        )
        return {status: count for status, count in self.session.execute(query)}

    def sum_profit_loss_since(self, since: datetime) -> Decimal:
        """Total realized P&L since `since`, for the same Summary Report
        use case above. `profit_loss` is only ever set once a signal
        closes (SUCCESSFUL/STOPPED_OUT) - still-open signals contribute
        nothing, not a NULL that would poison the sum."""
        query = select(func.coalesce(func.sum(Signal.profit_loss), 0)).where(
            Signal.created_at >= since
        )
        return Decimal(str(self.session.execute(query).scalar_one()))

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

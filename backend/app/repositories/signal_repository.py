import uuid
from collections.abc import Collection, Sequence
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import ColumnElement, Row, and_, func, or_, select

from app.config import settings
from app.models.enums import SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.repositories.base import BaseRepository


def _status_clause(status: SignalStatus, as_of: datetime | None) -> ColumnElement[bool]:
    """Rows with `status` - stored, or as a reader sees it at `as_of`.

    With `as_of` this is `status_resolver.effective_status` in SQL, so a list
    filtered by status agrees with the status each row shows (docs/04
    `GET /signals`). Workers pass no `as_of`: they need stored rows, such as a
    DRAFT past its window that the confirmation task still has to cancel."""
    stored = Signal.status == status
    if as_of is None:
        return stored

    draft_over = and_(
        Signal.status == SignalStatus.DRAFT,
        Signal.created_at <= as_of - timedelta(hours=settings.signal_confirmation_window_hours),
    )
    active_over = and_(
        Signal.status == SignalStatus.ACTIVE,
        Signal.created_at <= as_of - timedelta(hours=settings.signal_ttl_hours),
    )
    triggered_over = and_(
        Signal.status == SignalStatus.TRIGGERED,
        Signal.triggered_at.is_not(None),
        Signal.triggered_at <= as_of - timedelta(hours=settings.signal_triggered_ttl_hours),
    )
    if status is SignalStatus.DRAFT:
        return and_(stored, ~draft_over)
    if status is SignalStatus.CANCELLED:
        return or_(stored, draft_over)
    if status is SignalStatus.ACTIVE:
        return and_(stored, ~active_over)
    if status is SignalStatus.EXPIRED:
        return or_(stored, active_over)
    if status is SignalStatus.TRIGGERED:
        return and_(stored, ~triggered_over)
    if status is SignalStatus.CLOSED:
        return or_(stored, triggered_over)
    return stored


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
        as_of: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Signal]:
        """`timeframe` (docs/52 §2, added for AI Chat's "latest signal for
        this asset/timeframe" grounding lookup) is additive - every
        existing caller omits it and gets the prior unfiltered behavior.
        `as_of` matches `status` as readers see it then (`_status_clause`)."""
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(Signal.timeframe == timeframe)
        if status is not None:
            query = query.where(_status_clause(status, as_of))
        query = query.order_by(Signal.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(
        self,
        *,
        asset_id: uuid.UUID | None = None,
        timeframe: Timeframe | None = None,
        status: SignalStatus | None = None,
        as_of: datetime | None = None,
    ) -> int:
        query = select(Signal)
        if asset_id is not None:
            query = query.where(Signal.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(Signal.timeframe == timeframe)
        if status is not None:
            query = query.where(_status_clause(status, as_of))
        return self._count(query)

    def list_by_ids(self, signal_ids: Collection[uuid.UUID]) -> Sequence[Signal]:
        """Batch lookup - one query for a page of EA events or a batch of
        reports, instead of one per row (ADR-162)."""
        if not signal_ids:
            return []
        return self.session.execute(select(Signal).where(Signal.id.in_(signal_ids))).scalars().all()

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

    def list_status_times_since(
        self, since: datetime
    ) -> Sequence[Row[tuple[SignalStatus, datetime, datetime | None]]]:
        """`(status, created_at, triggered_at)` of every signal since `since`,
        for the Telegram bot's Summary Report button (§13). The caller
        counts them by the status a reader sees, which a stored-status
        GROUP BY cannot give: an unfilled signal past its TTL is still
        stored ACTIVE (ADR-088)."""
        query = select(Signal.status, Signal.created_at, Signal.triggered_at).where(
            Signal.created_at >= since
        )
        return self.session.execute(query).all()

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

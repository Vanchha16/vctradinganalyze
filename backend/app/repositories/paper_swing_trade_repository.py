import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, or_, select

from app.models.paper_swing_trade import PaperSwingTrade
from app.repositories.base import BaseRepository

TAKEN_STATUSES = ("open", "win", "loss", "timeout")


class PaperSwingTradeRepository(BaseRepository[PaperSwingTrade]):
    model = PaperSwingTrade

    def add(self, trade: PaperSwingTrade) -> PaperSwingTrade:
        self.session.add(trade)
        self.session.flush()
        return trade

    def exists(self, asset_id: uuid.UUID, direction: str, pivot_time: datetime) -> bool:
        query = select(PaperSwingTrade.id).where(
            PaperSwingTrade.asset_id == asset_id,
            PaperSwingTrade.direction == direction,
            PaperSwingTrade.pivot_time == pivot_time,
        )
        return self.session.execute(query).first() is not None

    def list_open(self, asset_id: uuid.UUID) -> Sequence[PaperSwingTrade]:
        query = select(PaperSwingTrade).where(
            PaperSwingTrade.asset_id == asset_id, PaperSwingTrade.status == "open"
        )
        return self.session.execute(query).scalars().all()

    def has_trade_open_at(self, asset_id: uuid.UUID, moment: datetime) -> bool:
        """True if a taken trade on this pair was open at `moment` - one
        trade per pair at a time, as in the backtest. A trade that closed
        exactly at `moment` no longer blocks."""
        query = select(PaperSwingTrade.id).where(
            PaperSwingTrade.asset_id == asset_id,
            PaperSwingTrade.status.in_(TAKEN_STATUSES),
            PaperSwingTrade.signal_time < moment,
            or_(PaperSwingTrade.closed_at.is_(None), PaperSwingTrade.closed_at > moment),
        )
        return self.session.execute(query).first() is not None

    def list_all(self) -> Sequence[PaperSwingTrade]:
        """Every record, oldest first - the statistics read the whole
        (small: about one setup a day) table."""
        query = select(PaperSwingTrade).order_by(PaperSwingTrade.signal_time.asc())
        return self.session.execute(query).scalars().all()

    def list_page(
        self,
        *,
        symbol: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[PaperSwingTrade], int]:
        query = self._filtered(symbol, status).order_by(PaperSwingTrade.signal_time.desc())
        rows = self.session.execute(self._paginate(query, offset=offset, limit=limit))
        return rows.scalars().all(), self._count(self._filtered(symbol, status))

    def _filtered(self, symbol: str | None, status: str | None) -> Select[tuple[PaperSwingTrade]]:
        query = self._query()
        if symbol is not None:
            query = query.where(PaperSwingTrade.symbol == symbol)
        if status == "taken":
            query = query.where(PaperSwingTrade.status.in_(TAKEN_STATUSES))
        elif status is not None:
            query = query.where(PaperSwingTrade.status == status)
        return query

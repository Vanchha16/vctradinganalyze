import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.tradingview_alert import TradingViewAlert
from app.repositories.base import BaseRepository


class TradingViewAlertRepository(BaseRepository[TradingViewAlert]):
    """ADR-146. Append-only in practice - the only mutation is stamping
    `delivered_at` after the Telegram notification fires."""

    model = TradingViewAlert

    def create(self, alert: TradingViewAlert) -> TradingViewAlert:
        self.session.add(alert)
        return alert

    def get_by_id(self, alert_id: uuid.UUID) -> TradingViewAlert | None:
        return self.session.get(TradingViewAlert, alert_id)

    def list_filtered(
        self,
        *,
        symbol: str | None = None,
        direction: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[TradingViewAlert]:
        """Newest first - an operator opening this page wants the alert
        that just arrived, mirroring `AuditLogRepository.list_admin`."""
        query = select(TradingViewAlert)
        if symbol:
            query = query.where(TradingViewAlert.symbol == symbol)
        if direction:
            query = query.where(TradingViewAlert.direction == direction)
        query = query.order_by(TradingViewAlert.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(self, *, symbol: str | None = None, direction: str | None = None) -> int:
        query = select(func.count()).select_from(TradingViewAlert)
        if symbol:
            query = query.where(TradingViewAlert.symbol == symbol)
        if direction:
            query = query.where(TradingViewAlert.direction == direction)
        return self.session.execute(query).scalar_one()


__all__ = ["TradingViewAlertRepository"]

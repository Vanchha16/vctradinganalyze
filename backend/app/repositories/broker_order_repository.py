import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.broker_order import BrokerOrder
from app.models.enums import OrderStatus
from app.repositories.base import BaseRepository


class BrokerOrderRepository(BaseRepository[BrokerOrder]):
    model = BrokerOrder

    def create(self, order: BrokerOrder) -> BrokerOrder:
        self.session.add(order)
        self.session.flush()
        return order

    def get_by_id(self, order_id: uuid.UUID) -> BrokerOrder | None:
        return self.session.get(BrokerOrder, order_id)

    def get_by_signal_id(self, signal_id: uuid.UUID) -> BrokerOrder | None:
        """One `BrokerOrder` per `Signal` (unique constraint on
        `signal_id`) - this is the lookup `signal_monitoring_tasks.py`'s
        §6 reconciliation fork uses to decide whether bridge state or
        candle-simulated touch logic drives a given signal's status."""
        query = select(BrokerOrder).where(BrokerOrder.signal_id == signal_id)
        return self.session.execute(query).scalars().first()

    def find_paginated(
        self,
        *,
        status: OrderStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[BrokerOrder]:
        query = select(BrokerOrder)
        if status is not None:
            query = query.where(BrokerOrder.status == status)
        query = query.order_by(BrokerOrder.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(self, *, status: OrderStatus | None = None) -> int:
        query = select(BrokerOrder)
        if status is not None:
            query = query.where(BrokerOrder.status == status)
        return self._count(query)

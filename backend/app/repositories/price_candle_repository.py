import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from app.models.enums import Timeframe
from app.models.price_candle import PriceCandle
from app.repositories.base import BaseRepository


class PriceCandleRepository(BaseRepository[PriceCandle]):
    model = PriceCandle

    def get_by_asset_timeframe_timestamp(
        self, asset_id: uuid.UUID, timeframe: Timeframe, timestamp: datetime
    ) -> PriceCandle | None:
        query = self._filter_by(
            self._query(), asset_id=asset_id, timeframe=timeframe, timestamp=timestamp
        )
        return self.session.execute(query).scalar_one_or_none()

    def get_latest(self, asset_id: uuid.UUID, timeframe: Timeframe) -> PriceCandle | None:
        query = (
            self._filter_by(self._query(), asset_id=asset_id, timeframe=timeframe)
            .order_by(PriceCandle.timestamp.desc())
            .limit(1)
        )
        return self.session.execute(query).scalar_one_or_none()

    def list_recent(
        self, asset_id: uuid.UUID, timeframe: Timeframe, *, limit: int = 500
    ) -> Sequence[PriceCandle]:
        """The most recent `limit` candles, returned oldest-first (the
        order every indicator function expects)."""
        query = (
            self._filter_by(self._query(), asset_id=asset_id, timeframe=timeframe)
            .order_by(PriceCandle.timestamp.desc())
            .limit(limit)
        )
        rows = self.session.execute(query).scalars().all()
        return list(reversed(rows))

    def list_range(
        self,
        asset_id: uuid.UUID,
        timeframe: Timeframe,
        *,
        start: datetime,
        end: datetime,
    ) -> Sequence[PriceCandle]:
        query = (
            select(PriceCandle)
            .where(
                PriceCandle.asset_id == asset_id,
                PriceCandle.timeframe == timeframe,
                PriceCandle.timestamp >= start,
                PriceCandle.timestamp <= end,
            )
            .order_by(PriceCandle.timestamp.asc())
        )
        return self.session.execute(query).scalars().all()

    def upsert(self, candle: PriceCandle) -> PriceCandle:
        """Insert a candle, or update it in place if one already exists for
        (asset_id, timeframe, timestamp) - see ADR-024.

        Implemented as an explicit get-then-write rather than a dialect-
        specific `ON CONFLICT` clause, so this repository behaves
        identically on SQLite (tests/verification) and Postgres
        (production) without dialect-specific branching.
        """
        existing = self.get_by_asset_timeframe_timestamp(
            candle.asset_id, candle.timeframe, candle.timestamp
        )
        if existing is None:
            self.session.add(candle)
            self.session.flush()
            return candle

        existing.open = candle.open
        existing.high = candle.high
        existing.low = candle.low
        existing.close = candle.close
        existing.volume = candle.volume
        self.session.flush()
        return existing

import uuid
from datetime import datetime

from app.models.enums import Timeframe
from app.models.smc_processing_state import SMCProcessingState
from app.repositories.base import BaseRepository


class SMCProcessingStateRepository(BaseRepository[SMCProcessingState]):
    model = SMCProcessingState

    def get_for_asset_timeframe(
        self, asset_id: uuid.UUID, timeframe: Timeframe
    ) -> SMCProcessingState | None:
        query = self._filter_by(self._query(), asset_id=asset_id, timeframe=timeframe)
        return self.session.execute(query).scalar_one_or_none()

    def upsert(
        self,
        asset_id: uuid.UUID,
        timeframe: Timeframe,
        *,
        last_processed_timestamp: datetime,
        engine_version: str,
    ) -> SMCProcessingState:
        existing = self.get_for_asset_timeframe(asset_id, timeframe)
        if existing is None:
            state = SMCProcessingState(
                asset_id=asset_id,
                timeframe=timeframe,
                last_processed_timestamp=last_processed_timestamp,
                engine_version=engine_version,
            )
            self.session.add(state)
            self.session.flush()
            return state

        existing.last_processed_timestamp = last_processed_timestamp
        existing.engine_version = engine_version
        self.session.flush()
        return existing

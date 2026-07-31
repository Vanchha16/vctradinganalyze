import uuid
from collections.abc import Sequence

from app.models.enums import Timeframe
from app.models.indicator_result import IndicatorResult
from app.repositories.base import BaseRepository


class IndicatorResultRepository(BaseRepository[IndicatorResult]):
    model = IndicatorResult

    def create(self, result: IndicatorResult) -> IndicatorResult:
        self.session.add(result)
        self.session.flush()
        return result

    def list_for_asset_timeframe(
        self,
        asset_id: uuid.UUID,
        timeframe: Timeframe,
        *,
        indicator: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[IndicatorResult]:
        filters: dict[str, object] = {"asset_id": asset_id, "timeframe": timeframe}
        if indicator is not None:
            filters["indicator"] = indicator
        query = self._filter_by(self._query(), **filters)
        return (
            self.session.execute(self._paginate(query, offset=offset, limit=limit)).scalars().all()
        )

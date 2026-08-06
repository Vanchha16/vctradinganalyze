import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from app.models.ai_analysis import AIAnalysis
from app.models.enums import Timeframe
from app.repositories.base import BaseRepository


class AIAnalysisRepository(BaseRepository[AIAnalysis]):
    model = AIAnalysis

    def create(self, analysis: AIAnalysis) -> AIAnalysis:
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def get_by_id(self, analysis_id: uuid.UUID) -> AIAnalysis | None:
        return self.session.get(AIAnalysis, analysis_id)

    def find_paginated(
        self,
        *,
        asset_id: uuid.UUID | None = None,
        timeframe: Timeframe | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[AIAnalysis]:
        """`timeframe` (docs/52 §2, added for AI Chat's "latest analysis
        for this asset/timeframe" grounding lookup) is additive - every
        existing caller omits it and gets the prior unfiltered behavior."""
        query = select(AIAnalysis)
        if asset_id is not None:
            query = query.where(AIAnalysis.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(AIAnalysis.timeframe == timeframe)
        query = query.order_by(AIAnalysis.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(
        self, *, asset_id: uuid.UUID | None = None, timeframe: Timeframe | None = None
    ) -> int:
        query = select(AIAnalysis)
        if asset_id is not None:
            query = query.where(AIAnalysis.asset_id == asset_id)
        if timeframe is not None:
            query = query.where(AIAnalysis.timeframe == timeframe)
        return self._count(query)

    def count_since(self, since: datetime) -> int:
        """Today's "AI analyses run" count (docs/58 §3.2, `GET /admin/system`)."""
        query = select(func.count()).select_from(AIAnalysis).where(AIAnalysis.created_at >= since)
        return self.session.execute(query).scalar_one()

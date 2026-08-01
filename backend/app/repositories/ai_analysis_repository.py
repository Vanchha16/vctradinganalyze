import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.ai_analysis import AIAnalysis
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
        self, *, asset_id: uuid.UUID | None = None, offset: int = 0, limit: int = 20
    ) -> Sequence[AIAnalysis]:
        query = select(AIAnalysis)
        if asset_id is not None:
            query = query.where(AIAnalysis.asset_id == asset_id)
        query = query.order_by(AIAnalysis.created_at.desc()).offset(offset).limit(limit)
        return self.session.execute(query).scalars().all()

    def count_filtered(self, *, asset_id: uuid.UUID | None = None) -> int:
        query = select(AIAnalysis)
        if asset_id is not None:
            query = query.where(AIAnalysis.asset_id == asset_id)
        return self._count(query)

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CreatedAtMixin, UUIDMixin
from app.models.enums import Recommendation, Timeframe


class AIAnalysis(Base, UUIDMixin, CreatedAtMixin):
    """A persisted AI Orchestrator result (docs/03 §10, docs/50 §2,
    ADR-082). Uses CreatedAtMixin (not TimestampMixin) - an analysis row
    represents "what was recommended at time X," never rewritten in
    place, the same append-only reasoning already applied to
    `NewsArticle` (ADR-053). The first genuinely persisted engine output
    in this project: unlike every Phase 4/5 deterministic engine, an LLM
    call is not perfectly reproducible on replay, so persisting it is
    justified for the first time (ADR-015's replayability requirement).

    `confidence_level`/`risk_level`/`execution_guidance` are stored as
    plain strings, not native DB enums - this table doesn't own those
    concepts, it only echoes values already computed and versioned
    independently by `AnalysisConfidenceEngine`/`RiskManagementEngine`;
    a native enum here would need its own migration every time either
    upstream engine's enum changes. `recommendation` IS owned by this
    table (the new concept Phase 6A introduces), so it gets a real
    native enum.
    """

    __tablename__ = "ai_analysis"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    timeframe: Mapped[Timeframe] = mapped_column(
        SAEnum(Timeframe, name="candle_timeframe", native_enum=True), nullable=False
    )
    recommendation: Mapped[Recommendation] = mapped_column(
        SAEnum(Recommendation, name="ai_recommendation", native_enum=True), nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    execution_guidance: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reasoning: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    supporting_evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    conflicting_evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    invalidation_conditions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    ai_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

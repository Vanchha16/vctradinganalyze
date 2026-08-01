import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Recommendation, Timeframe


class ReasoningResponse(BaseModel):
    """docs/50 §7 - the AI Orchestrator's ONLY AI-generated field. Every
    other field on `AIAnalysisResponse` is deterministic (ADR-079)."""

    model_config = ConfigDict(from_attributes=True)

    summary: str
    technical: str
    smc: str
    economic: str
    news: str
    risk: str
    conclusion: str


class AIAnalysisResponse(BaseModel):
    """docs/04 §AI Analysis, docs/50 §1. `recommendation`/`confidence_score`/
    `confidence_level`/`risk_level`/`entry_price`/`stop_loss`/`take_profit`/
    `execution_guidance`/`supporting_evidence`/`conflicting_evidence`/
    `risks`/`invalidation_conditions` are all deterministic - only
    `reasoning`'s sections are AI-generated (ADR-078/079)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "8ddb570a-457b-4ca7-87fb-df740998cc2f",
                "symbol": "EURUSD",
                "timeframe": "h1",
                "recommendation": "buy",
                "confidence_score": 87.0,
                "confidence_level": "high",
                "risk_level": "medium",
                "entry_price": 1.17540,
                "stop_loss": 1.17120,
                "take_profit": 1.18150,
                "execution_guidance": "normal",
                "reasoning": {
                    "summary": "...",
                    "technical": "...",
                    "smc": "...",
                    "economic": "...",
                    "news": "...",
                    "risk": "...",
                    "conclusion": "...",
                },
                "supporting_evidence": [],
                "conflicting_evidence": [],
                "risks": [],
                "invalidation_conditions": [],
                "model_name": "gpt-4o-mini",
                "prompt_version": "1.0.0",
                "ai_available": True,
                "warnings": [],
                "calculated_at": "2026-08-01T12:00:00Z",
            }
        },
    )

    id: uuid.UUID
    symbol: str
    timeframe: Timeframe
    recommendation: Recommendation
    confidence_score: float
    confidence_level: str
    risk_level: str | None
    entry_price: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    execution_guidance: str | None
    reasoning: ReasoningResponse
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    risks: list[str]
    invalidation_conditions: list[str]
    model_name: str
    prompt_version: str
    ai_available: bool
    warnings: list[str]
    calculated_at: datetime


class AIAnalysisListResponse(BaseModel):
    items: list[AIAnalysisResponse]
    page: int = Field(examples=[1])
    limit: int = Field(examples=[20])
    total: int = Field(examples=[2])

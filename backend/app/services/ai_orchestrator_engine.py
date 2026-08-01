"""Top-level AI Orchestrator engine (docs/07, docs/13, docs/50).

Combines what docs/07 calls "orchestration" and docs/13 calls
"reasoning" into one class (ADR-077). Every field on `AIAnalysisResult`
except `reasoning` is deterministic - reused from an existing engine or
computed by a new deterministic module (ADR-078/079/080). The LLM's sole
output is `reasoning`'s narrative text, and even a total LLM failure
never blocks the response (ADR-081) - it only degrades `reasoning` to a
deterministic template and sets `ai_available=False`.
"""

import logging
import time
from datetime import UTC, datetime
from decimal import Decimal

from app.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import Recommendation, Timeframe
from app.repositories.ai_analysis_repository import AIAnalysisRepository

from .ai_orchestrator import (
    evidence_extractor,
    invalidation_builder,
    prompt_builder,
    response_parser,
    summary_fallback,
)
from .ai_orchestrator import recommendation_decision as recommendation_decision_module
from .ai_orchestrator.context_builder import ContextBuilder
from .ai_orchestrator.evidence_extractor import ExtractedEvidence
from .ai_orchestrator.providers.base import AIGenerationRequest, AIProvider
from .ai_orchestrator.providers.exceptions import AIProviderError, TransientAIProviderError
from .ai_orchestrator.recommendation_decision import RecommendationDecision
from .ai_orchestrator.types import AIAnalysisResult, AnalysisContext, ReasoningSections

logger = logging.getLogger(__name__)


class AIOrchestratorEngine:
    def __init__(
        self,
        context_builder: ContextBuilder,
        provider: AIProvider,
        ai_analysis_repository: AIAnalysisRepository,
    ) -> None:
        self._context_builder = context_builder
        self._provider = provider
        self._ai_analysis_repository = ai_analysis_repository

    def generate(self, asset: Asset, timeframe: Timeframe) -> AIAnalysisResult:
        start = time.monotonic()
        calculated_at = datetime.now(UTC)

        context = self._context_builder.build(asset, timeframe)
        decision = recommendation_decision_module.decide(context)
        extracted = evidence_extractor.extract(context)
        conditions = invalidation_builder.build(context, decision.recommendation)

        reasoning, ai_available, model_name, warnings = self._narrate(context, decision, extracted)

        latency_ms = round((time.monotonic() - start) * 1000)

        confidence_level = context.confidence.confidence_level.value
        risk_level = context.risk.risk_level.value if context.risk is not None else None
        execution_guidance = (
            context.risk.position_guidance.value
            if context.risk is not None and context.risk.position_guidance is not None
            else None
        )
        candidate = context.candidate_setup

        row = self._persist(
            asset=asset,
            timeframe=timeframe,
            recommendation=decision.recommendation,
            confidence_score=context.confidence.overall_confidence,
            confidence_level=confidence_level,
            risk_level=risk_level,
            entry_price=candidate.entry_price if candidate is not None else None,
            stop_loss=candidate.stop_loss if candidate is not None else None,
            take_profit=candidate.take_profit if candidate is not None else None,
            execution_guidance=execution_guidance,
            reasoning=reasoning,
            model_name=model_name,
            ai_available=ai_available,
            latency_ms=latency_ms,
            supporting_evidence=extracted.supporting_evidence,
            conflicting_evidence=extracted.conflicting_evidence,
            risks=extracted.risks,
            invalidation_conditions=conditions,
            warnings=warnings,
        )

        return AIAnalysisResult(
            id=row.id,
            symbol=asset.symbol,
            timeframe=timeframe,
            recommendation=decision.recommendation,
            confidence_score=context.confidence.overall_confidence,
            confidence_level=confidence_level,
            risk_level=risk_level,
            entry_price=candidate.entry_price if candidate is not None else None,
            stop_loss=candidate.stop_loss if candidate is not None else None,
            take_profit=candidate.take_profit if candidate is not None else None,
            execution_guidance=execution_guidance,
            reasoning=reasoning,
            model_name=model_name,
            prompt_version=prompt_builder.PROMPT_VERSION,
            ai_available=ai_available,
            calculated_at=calculated_at,
            supporting_evidence=extracted.supporting_evidence,
            conflicting_evidence=extracted.conflicting_evidence,
            risks=extracted.risks,
            invalidation_conditions=conditions,
            warnings=warnings,
        )

    def _narrate(
        self,
        context: AnalysisContext,
        decision: RecommendationDecision,
        extracted: ExtractedEvidence,
    ) -> tuple[ReasoningSections, bool, str, list[str]]:
        request = AIGenerationRequest(
            system_prompt=prompt_builder.SYSTEM_PROMPT,
            user_prompt=prompt_builder.build_user_prompt(
                context,
                decision.recommendation,
                decision.reasons,
                extracted.supporting_evidence,
                extracted.conflicting_evidence,
                extracted.risks,
            ),
            json_schema=prompt_builder.reasoning_json_schema(),
            max_tokens=prompt_builder.max_tokens(),
        )

        warnings: list[str] = []
        last_error: Exception | None = None

        for attempt in range(1, settings.ai_retry_max_attempts + 1):
            try:
                response = self._provider.generate(request)
                reasoning = response_parser.parse(response.raw_content)
                return reasoning, True, response.model_name, warnings
            except AIProviderError as exc:
                last_error = exc
                logger.warning(
                    "ai_orchestrator.provider_call_failed",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                if not isinstance(exc, TransientAIProviderError):
                    break
                continue

        warnings.append(f"AI narration unavailable ({last_error}) - deterministic summary shown.")
        fallback = summary_fallback.build(context, decision.recommendation, decision.reasons)
        return fallback, False, "none", warnings

    def _persist(
        self,
        *,
        asset: Asset,
        timeframe: Timeframe,
        recommendation: Recommendation,
        confidence_score: float,
        confidence_level: str,
        risk_level: str | None,
        entry_price: Decimal | None,
        stop_loss: Decimal | None,
        take_profit: Decimal | None,
        execution_guidance: str | None,
        reasoning: ReasoningSections,
        model_name: str,
        ai_available: bool,
        latency_ms: int,
        supporting_evidence: list[str],
        conflicting_evidence: list[str],
        risks: list[str],
        invalidation_conditions: list[str],
        warnings: list[str],
    ) -> AIAnalysis:
        row = AIAnalysis(
            asset_id=asset.id,
            timeframe=timeframe,
            recommendation=recommendation,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            risk_level=risk_level,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            execution_guidance=execution_guidance,
            reasoning={
                "summary": reasoning.summary,
                "technical": reasoning.technical,
                "smc": reasoning.smc,
                "economic": reasoning.economic,
                "news": reasoning.news,
                "risk": reasoning.risk,
                "conclusion": reasoning.conclusion,
            },
            supporting_evidence=supporting_evidence,
            conflicting_evidence=conflicting_evidence,
            risks=risks,
            invalidation_conditions=invalidation_conditions,
            model_name=model_name,
            prompt_version=prompt_builder.PROMPT_VERSION,
            ai_available=ai_available,
            latency_ms=latency_ms,
            warnings=warnings,
        )
        self._ai_analysis_repository.create(row)
        self._ai_analysis_repository.commit()
        return row

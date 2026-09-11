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
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

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
    risk_review,
    summary_fallback,
)
from .ai_orchestrator import recommendation_decision as recommendation_decision_module
from .ai_orchestrator.context_builder import ContextBuilder
from .ai_orchestrator.evidence_extractor import ExtractedEvidence
from .ai_orchestrator.providers.base import AIGenerationRequest, AIProvider
from .ai_orchestrator.providers.exceptions import AIProviderError, TransientAIProviderError
from .ai_orchestrator.recommendation_decision import RecommendationDecision
from .ai_orchestrator.risk_review import RiskReview, RiskReviewMode, RiskReviewVerdict
from .ai_orchestrator.types import AIAnalysisResult, AnalysisContext, ReasoningSections

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _Narration:
    """What `_narrate` produced, including the provider's own token
    counts (ADR-149). `input_tokens`/`output_tokens` are `None` whenever
    the provider did not report usage - and always on the deterministic
    fallback path, where no LLM call happened at all."""

    reasoning: ReasoningSections
    ai_available: bool
    model_name: str
    warnings: list[str]
    input_tokens: int | None = None
    output_tokens: int | None = None


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

    def generate(
        self, asset: Asset, timeframe: Timeframe, focus_event_id: UUID | None = None
    ) -> AIAnalysisResult:
        """`focus_event_id` (ADR-152) names one economic release the
        caller wants the narration to address. It changes only the
        prompt - never the recommendation, which stays deterministic
        (ADR-079)."""
        start = time.monotonic()
        calculated_at = datetime.now(UTC)

        context = self._context_builder.build(asset, timeframe, focus_event_id)
        decision = recommendation_decision_module.decide(context)
        extracted = evidence_extractor.extract(context)

        # ADR-167. Reviewed before narrating, so an enforced veto is what the
        # explanation then describes. A downgrade only - nothing here can turn
        # WAIT into a trade.
        review, review_warnings = self._review(context, decision, extracted)
        if (
            review is not None
            and review.mode is RiskReviewMode.ENFORCE
            and review.verdict is RiskReviewVerdict.VETO
        ):
            decision = RecommendationDecision(
                recommendation=Recommendation.WAIT,
                reasons=[f"AI risk review vetoed the setup: {review.key_risk}"],
            )
        conditions = invalidation_builder.build(context, decision.recommendation)

        narration = self._narrate(context, decision, extracted)
        warnings = [*narration.warnings, *review_warnings]

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
            reasoning=narration.reasoning,
            model_name=narration.model_name,
            ai_available=narration.ai_available,
            latency_ms=latency_ms,
            input_tokens=narration.input_tokens,
            output_tokens=narration.output_tokens,
            supporting_evidence=extracted.supporting_evidence,
            conflicting_evidence=extracted.conflicting_evidence,
            risks=extracted.risks,
            invalidation_conditions=conditions,
            warnings=warnings,
            risk_review=review,
        )

        return AIAnalysisResult(
            id=row.id,
            symbol=asset.symbol,
            timeframe=timeframe,
            #: ADR-147: carried through so a persisted `Signal` can record
            #: which strategy produced it. Already computed by
            #: `ContextBuilder`; it was simply discarded here before.
            strategy=context.strategy.primary_strategy,
            recommendation=decision.recommendation,
            confidence_score=context.confidence.overall_confidence,
            confidence_level=confidence_level,
            risk_level=risk_level,
            entry_price=candidate.entry_price if candidate is not None else None,
            stop_loss=candidate.stop_loss if candidate is not None else None,
            take_profit=candidate.take_profit if candidate is not None else None,
            execution_guidance=execution_guidance,
            reasoning=narration.reasoning,
            model_name=narration.model_name,
            prompt_version=prompt_builder.PROMPT_VERSION,
            ai_available=narration.ai_available,
            calculated_at=calculated_at,
            supporting_evidence=extracted.supporting_evidence,
            conflicting_evidence=extracted.conflicting_evidence,
            risks=extracted.risks,
            invalidation_conditions=conditions,
            warnings=warnings,
            risk_review=review,
        )

    def _narrate(
        self,
        context: AnalysisContext,
        decision: RecommendationDecision,
        extracted: ExtractedEvidence,
    ) -> _Narration:
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
                return _Narration(
                    reasoning=reasoning,
                    ai_available=True,
                    model_name=response.model_name,
                    warnings=warnings,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                )
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
        return _Narration(
            reasoning=fallback, ai_available=False, model_name="none", warnings=warnings
        )

    def _review(
        self,
        context: AnalysisContext,
        decision: RecommendationDecision,
        extracted: ExtractedEvidence,
    ) -> tuple[RiskReview | None, list[str]]:
        """ADR-167. One attempt, no retry: a missing verdict costs nothing
        but the verdict, while a retry doubles the spend on the calls most
        likely to fail again. Returns the review (or None) and any warning."""
        try:
            mode = RiskReviewMode(settings.ai_risk_review_mode.lower())
        except ValueError:
            logger.warning(
                "ai_orchestrator.risk_review_mode_invalid",
                extra={"value": settings.ai_risk_review_mode},
            )
            mode = RiskReviewMode.OFF

        if mode is RiskReviewMode.OFF or decision.recommendation is Recommendation.WAIT:
            return None, []

        evidence = prompt_builder.build_user_prompt(
            context,
            decision.recommendation,
            decision.reasons,
            extracted.supporting_evidence,
            extracted.conflicting_evidence,
            extracted.risks,
        )
        request = AIGenerationRequest(
            system_prompt=risk_review.SYSTEM_PROMPT,
            user_prompt=risk_review.build_user_prompt(evidence),
            json_schema=risk_review.json_schema(),
            max_tokens=risk_review.MAX_TOKENS,
        )
        try:
            response = self._provider.generate(request)
            verdict, reasons, key_risk = risk_review.parse(response.raw_content)
        except AIProviderError as exc:
            logger.warning("ai_orchestrator.risk_review_unavailable", extra={"error": str(exc)})
            return None, [f"AI risk review unavailable ({exc}) - no verdict recorded."]

        return (
            RiskReview(
                verdict=verdict,
                reasons=reasons,
                key_risk=key_risk,
                mode=mode,
                model_name=response.model_name,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            ),
            [],
        )

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
        input_tokens: int | None,
        output_tokens: int | None,
        supporting_evidence: list[str],
        conflicting_evidence: list[str],
        risks: list[str],
        invalidation_conditions: list[str],
        warnings: list[str],
        risk_review: RiskReview | None,
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
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            warnings=warnings,
            risk_review_verdict=risk_review.verdict.value if risk_review is not None else None,
            risk_review_mode=risk_review.mode.value if risk_review is not None else None,
            risk_review_reasons=risk_review.reasons if risk_review is not None else None,
            risk_review_key_risk=risk_review.key_risk if risk_review is not None else None,
            risk_review_model=risk_review.model_name if risk_review is not None else None,
            risk_review_input_tokens=risk_review.input_tokens if risk_review is not None else None,
            risk_review_output_tokens=(
                risk_review.output_tokens if risk_review is not None else None
            ),
        )
        self._ai_analysis_repository.create(row)
        self._ai_analysis_repository.commit()
        return row

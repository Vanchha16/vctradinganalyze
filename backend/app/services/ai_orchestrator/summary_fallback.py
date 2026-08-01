"""Deterministic template `reasoning`, used only when the AI provider is
unavailable or its response could not be recovered (docs/50 §9). Mirrors
`app.services.analysis_confidence.summary_builder`'s no-AI-generated-text
precedent - never blocks the response, `ai_available` is set to False by
the caller when this path is used."""

from app.models.enums import Recommendation

from .types import AnalysisContext, ReasoningSections


def build(
    context: AnalysisContext, recommendation: Recommendation, reasons: list[str]
) -> ReasoningSections:
    reason_text = " ".join(reasons) if reasons else "Evidence supports this recommendation."
    summary = (
        f"{context.asset.symbol} on {context.timeframe.value}: {recommendation.value.upper()} "
        f"at {context.confidence.overall_confidence:.0f}% confidence. {reason_text} "
        "(AI narration unavailable - deterministic summary shown.)"
    )
    placeholder = "AI narration is unavailable for this section."
    return ReasoningSections(
        summary=summary,
        technical=placeholder,
        smc=placeholder,
        economic=placeholder,
        news=placeholder,
        risk=placeholder,
        conclusion=summary,
    )

"""Deterministic, template-based summary sentence (docs/45 §8). Built
only from already-computed evidence via fixed string templates - no
language generation, no AI, no free-form text. Always 2-3 sentences.
"""

from app.services.analysis_confidence.types import (
    AlignmentEvidence,
    ConfidenceLevel,
    ConflictEvidence,
)

_LEVEL_LABEL: dict[ConfidenceLevel, str] = {
    ConfidenceLevel.VERY_LOW: "very low",
    ConfidenceLevel.LOW: "low",
    ConfidenceLevel.MODERATE: "moderate",
    ConfidenceLevel.HIGH: "high",
    ConfidenceLevel.VERY_HIGH: "very high",
}


def build(
    overall_confidence: float,
    confidence_level: ConfidenceLevel,
    alignment: AlignmentEvidence,
    conflicts: list[ConflictEvidence],
    missing_data: list[str],
) -> str:
    engine_count = sum(
        1
        for d in (
            alignment.technical_direction,
            alignment.smc_direction,
            alignment.regime_direction,
        )
        if d is not None
    )
    agreeing_count = round(alignment.agreement_ratio * engine_count) if engine_count else 0

    sentence_one = (
        f"Confidence is {_LEVEL_LABEL[confidence_level]} "
        f"({overall_confidence:.0f}/100) with {agreeing_count} of {engine_count} "
        f"available engines in directional agreement."
    )

    if conflicts:
        sentence_two = f"{len(conflicts)} cross-engine conflict(s) detected."
    else:
        sentence_two = "No cross-engine conflicts detected."

    sentences = [sentence_one, sentence_two]

    if missing_data:
        sentences.append(
            f"{len(missing_data)} data quality issue(s) noted: {', '.join(missing_data)}."
        )

    return " ".join(sentences)

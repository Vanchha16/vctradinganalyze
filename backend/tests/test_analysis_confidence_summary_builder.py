import re

from app.services.analysis_confidence import alignment_analyzer, summary_builder
from app.services.analysis_confidence.types import (
    ConfidenceLevel,
    ConflictEvidence,
    ConflictSeverity,
    NormalizedDirection,
)

_FULL_AGREEMENT = alignment_analyzer.analyze(
    NormalizedDirection.BULLISH, NormalizedDirection.BULLISH, NormalizedDirection.BULLISH
)


def test_summary_is_two_sentences_with_no_missing_data() -> None:
    summary = summary_builder.build(80.0, ConfidenceLevel.VERY_HIGH, _FULL_AGREEMENT, [], [])

    assert summary.count(".") == 2
    assert "very high" in summary
    assert "80/100" in summary
    assert "No cross-engine conflicts" in summary


def test_summary_mentions_conflict_count() -> None:
    conflicts = [
        ConflictEvidence(
            description="x", severity=ConflictSeverity.HIGH, engines_involved=["technical_analysis"]
        )
    ]
    summary = summary_builder.build(40.0, ConfidenceLevel.LOW, _FULL_AGREEMENT, conflicts, [])

    assert "1 cross-engine conflict(s) detected." in summary


def test_summary_includes_missing_data_as_third_sentence() -> None:
    summary = summary_builder.build(
        20.0, ConfidenceLevel.VERY_LOW, _FULL_AGREEMENT, [], ["technical_analysis_unavailable"]
    )

    assert summary.count(".") == 3
    assert "technical_analysis_unavailable" in summary


def test_summary_contains_no_ai_disclaimer_language() -> None:
    summary = summary_builder.build(50.0, ConfidenceLevel.MODERATE, _FULL_AGREEMENT, [], [])

    for banned in ("i think", "probably", "predict", "recommend"):
        assert banned not in summary.lower()
    assert re.search(r"\bai\b", summary.lower()) is None

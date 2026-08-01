from dataclasses import replace

from app.services.ai_orchestrator.evidence_extractor import extract
from app.services.analysis_confidence.types import ConflictEvidence, ConflictSeverity
from tests.ai_orchestrator_helpers import make_analysis_context, make_confidence_result


def test_extract_supporting_evidence_from_technical_and_smc() -> None:
    context = make_analysis_context()
    result = extract(context)
    assert any("Technical Analysis trend" in e for e in result.supporting_evidence)
    assert any("Break of Structure confirmed" in e for e in result.supporting_evidence)
    assert any("Strategy Engine favors" in e for e in result.supporting_evidence)


def test_extract_conflicting_evidence_from_confidence_conflicts() -> None:
    conflict = ConflictEvidence(
        description="Technical vs SMC disagree", severity=ConflictSeverity.HIGH, engines_involved=[]
    )
    confidence = make_confidence_result()
    confidence = replace(confidence, conflicts=[conflict])
    context = make_analysis_context(confidence=confidence)

    result = extract(context)

    assert "Technical vs SMC disagree" in result.conflicting_evidence


def test_extract_risks_empty_when_nothing_present() -> None:
    context = make_analysis_context()
    result = extract(context)
    assert result.risks == []

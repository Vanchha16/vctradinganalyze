from app.services.analysis_confidence import alignment_analyzer
from app.services.analysis_confidence.types import NormalizedDirection


def test_all_three_engines_agree() -> None:
    result = alignment_analyzer.analyze(
        NormalizedDirection.BULLISH, NormalizedDirection.BULLISH, NormalizedDirection.BULLISH
    )

    assert result.agreement_ratio == 1.0
    assert result.agreement_score == alignment_analyzer.CROSS_ENGINE_AGREEMENT_WEIGHT


def test_two_of_three_agree() -> None:
    result = alignment_analyzer.analyze(
        NormalizedDirection.BULLISH, NormalizedDirection.BULLISH, NormalizedDirection.BEARISH
    )

    assert result.agreement_ratio == 2 / 3


def test_all_three_disagree() -> None:
    result = alignment_analyzer.analyze(
        NormalizedDirection.BULLISH, NormalizedDirection.BEARISH, NormalizedDirection.NEUTRAL
    )

    assert result.agreement_ratio == 1 / 3


def test_partial_unavailable_only_counts_available_engines() -> None:
    result = alignment_analyzer.analyze(
        NormalizedDirection.BULLISH, NormalizedDirection.BULLISH, None
    )

    assert result.agreement_ratio == 1.0
    assert result.regime_direction is None


def test_all_unavailable_has_zero_agreement() -> None:
    result = alignment_analyzer.analyze(None, None, None)

    assert result.agreement_ratio == 0.0
    assert result.agreement_score == 0.0

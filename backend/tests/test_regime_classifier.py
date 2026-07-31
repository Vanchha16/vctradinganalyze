from app.services.market_regime.regime_classifier import MIN_MARGIN, classify
from app.services.market_regime.types import MarketRegimeState, RegimeCandidate


def _candidate(regime: MarketRegimeState, confidence: float, precedence: int) -> RegimeCandidate:
    return RegimeCandidate(regime=regime, confidence=confidence, precedence=precedence)


def test_uncertain_when_no_candidate_qualifies() -> None:
    candidates = [
        _candidate(MarketRegimeState.TRENDING_BULLISH, 40.0, 4),
        _candidate(MarketRegimeState.RANGING, 30.0, 6),
    ]

    outcome = classify(candidates)

    assert outcome.regime == MarketRegimeState.UNCERTAIN
    assert outcome.winner is None


def test_precedence_wins_among_qualifying_candidates_even_if_not_highest_confidence() -> None:
    # Ranging has the highest raw confidence, but Breakout has higher
    # precedence (lower number) and also qualifies - Breakout must win,
    # confirming precedence is applied only among qualifying candidates,
    # not simply "highest confidence wins" (Phase 4C refinement).
    candidates = [
        _candidate(MarketRegimeState.RANGING, 95.0, 6),
        _candidate(MarketRegimeState.BREAKOUT, 61.0, 2),
        _candidate(MarketRegimeState.PULLBACK, 10.0, 5),
    ]

    outcome = classify(candidates)

    assert outcome.regime == MarketRegimeState.BREAKOUT


def test_non_qualifying_candidates_never_win_despite_precedence() -> None:
    candidates = [
        _candidate(MarketRegimeState.REVERSAL, 30.0, 1),  # does not qualify
        _candidate(MarketRegimeState.RANGING, 80.0, 6),
    ]

    outcome = classify(candidates)

    assert outcome.regime == MarketRegimeState.RANGING


def test_thin_margin_applies_stability_penalty_and_warning() -> None:
    candidates = [
        _candidate(MarketRegimeState.ACCUMULATION, 70.0, 3),
        _candidate(MarketRegimeState.DISTRIBUTION, 65.0, 3),
    ]

    outcome = classify(candidates)

    assert outcome.regime == MarketRegimeState.ACCUMULATION
    assert outcome.stability_penalty < 0.0
    assert len(outcome.warnings) == 1
    assert 70.0 - 65.0 < MIN_MARGIN


def test_wide_margin_has_no_stability_penalty() -> None:
    candidates = [
        _candidate(MarketRegimeState.TRENDING_BULLISH, 90.0, 4),
        _candidate(MarketRegimeState.RANGING, 40.0, 6),
    ]

    outcome = classify(candidates)

    assert outcome.stability_penalty == 0.0
    assert outcome.warnings == []

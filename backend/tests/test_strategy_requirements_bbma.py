"""BBMA requirements checklist (ADR-148, docs/61).

Unlike the other checklists, BBMA's evidence comes from its own detector
rather than from Technical/SMC/Regime, so these build `BBMAResult`
directly.
"""

from app.services.bbma.types import (
    BBMAConditions,
    BBMADirection,
    BBMAResult,
    BBMASetup,
    BBMASetupKind,
)
from app.services.strategy.requirements import bbma as bbma_requirements
from tests.strategy_helpers import make_evidence_bundle


def _setup(*, direction: BBMADirection = BBMADirection.SELL, entry_index: int = 50) -> BBMASetup:
    return BBMASetup(
        kind=BBMASetupKind.EXTREME,
        direction=direction,
        entry_index=entry_index,
        marked_level=103.0,
        entry_price=102.0,
        stop_loss=105.0,
        take_profit=98.0,
    )


def _conditions(
    *,
    trend_major: BBMADirection | None = BBMADirection.SELL,
    bb_expanding: bool = True,
) -> BBMAConditions:
    return BBMAConditions(
        csm=False,
        csak=False,
        csk=False,
        zzl=False,
        trend_major=trend_major,
        bb_expanding=bb_expanding,
    )


def _result(setups: list[BBMASetup], conditions: BBMAConditions | None) -> BBMAResult:
    return BBMAResult(symbol="XAUUSD", timeframe="h1", setups=setups, conditions=conditions)


def test_no_bbma_evidence_scores_zero_without_raising() -> None:
    """The bundle's `bbma` is `None` whenever there were no candles - the
    same graceful degradation the other checklists apply to `technical`."""
    result = bbma_requirements.check(make_evidence_bundle(bbma=None))

    assert result.met_count == 0
    assert result.total_count == 4


def test_full_bbma_setup_meets_every_requirement() -> None:
    evidence = make_evidence_bundle(
        bbma=_result([_setup()], _conditions(trend_major=BBMADirection.SELL, bb_expanding=True))
    )

    result = bbma_requirements.check(evidence)

    assert result.met_count == 4
    assert result.ratio == 1.0


def test_setup_against_the_trend_major_scores_lower() -> None:
    """docs/61 §2.2 - "an Extreme against the trend major is a weak
    Extreme". A SELL setup while price sits above EMA50 loses that
    requirement rather than being rejected outright."""
    evidence = make_evidence_bundle(
        bbma=_result(
            [_setup(direction=BBMADirection.SELL)],
            _conditions(trend_major=BBMADirection.BUY),
        )
    )

    result = bbma_requirements.check(evidence)

    assert result.met_count == 3


def test_flat_bollinger_bands_score_lower() -> None:
    """Flat BB means no momentum and price oscillating between the bands
    (docs/61 §2) - a poor environment for a directional entry."""
    evidence = make_evidence_bundle(bbma=_result([_setup()], _conditions(bb_expanding=False)))

    result = bbma_requirements.check(evidence)

    assert result.met_count == 3


def test_detected_structure_without_conditions_scores_zero() -> None:
    """`conditions` is `None` when the latest bar had no Bollinger value
    at all - there is nothing to judge the setup against."""
    evidence = make_evidence_bundle(bbma=_result([_setup()], None))

    result = bbma_requirements.check(evidence)

    assert result.met_count == 0

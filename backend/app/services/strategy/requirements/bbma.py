"""BBMA requirements checklist (docs/61, ADR-148).

Unlike the other seven checklists, which read already-computed
Technical/SMC/Regime evidence, BBMA's requirements come from its own
detector - the structure it looks for (Extreme, reverse, retest) exists
nowhere else in this project.

Four requirements, matching how docs/61 §3.1 validates a setup plus the
trend-major filter of §2.2. Every one is derived from the source
material; none is invented here.
"""

from app.services.bbma.types import BBMAResult, BBMASetup, BBMASetupKind
from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle

#: A setup older than this many bars behind the latest candle is history,
#: not a tradeable setup. Invented (docs/61 §7.3's class of gap) - the
#: source describes the sequence but never says how long a completed
#: setup stays actionable.
_MAX_SETUP_AGE_BARS = 3


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    bbma = evidence.bbma
    if bbma is None or bbma.conditions is None:
        return RequirementsResult(met_count=0, total_count=4)

    setup = bbma.latest

    # 1. A complete BBMA setup exists at all - Extreme/MHV/Re-entry, each
    #    of which already required its own reverse and retest to be
    #    detected (docs/61 §3).
    has_setup = setup is not None and setup.kind in {
        BBMASetupKind.EXTREME,
        BBMASetupKind.MHV,
        BBMASetupKind.RE_ENTRY,
    }

    # 2. It is recent enough to act on rather than a historical artefact.
    is_current = is_fresh(bbma, setup)

    # 3. It agrees with the trend major (docs/61 §2.2) - "an Extreme
    #    against the trend major is a weak Extreme".
    agrees_with_trend = (
        setup is not None
        and bbma.conditions.trend_major is not None
        and setup.direction is bbma.conditions.trend_major
    )

    # 4. Bollinger Bands are expanding, not flat. Flat BB means no
    #    momentum and price simply oscillating between the bands
    #    (docs/61 §2) - a poor environment for a directional BBMA entry.
    has_momentum_context = bbma.conditions.bb_expanding

    met_count = sum([has_setup, is_current, agrees_with_trend, has_momentum_context])
    return RequirementsResult(met_count=met_count, total_count=4)


def is_fresh(bbma_result: BBMAResult, setup: BBMASetup | None) -> bool:
    """Whether `setup` completed within the last `_MAX_SETUP_AGE_BARS`
    candles the detector saw.

    ADR-179 fixed this. It used to measure against the newest *setup*
    rather than the newest *candle*, so the latest setup was always judged
    current - an Extreme from fifty candles ago counted as fresh. That was
    harmless-ish while BBMA only picked a label; once the order is priced
    at the setup's own marked level (ADR-179), a stale setup would place an
    order at a price the market left long ago. Unknown length is treated
    as not fresh.
    """
    if setup is None or setup.entry_index < 0 or bbma_result.bar_count <= 0:
        return False
    latest_index = bbma_result.bar_count - 1
    return setup.entry_index >= latest_index - _MAX_SETUP_AGE_BARS


__all__ = ["check", "is_fresh"]

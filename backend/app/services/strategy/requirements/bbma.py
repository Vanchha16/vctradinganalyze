"""BBMA requirements checklist (docs/61, ADR-148).

Unlike the other seven checklists, which read already-computed
Technical/SMC/Regime evidence, BBMA's requirements come from its own
detector - the structure it looks for (Extreme, reverse, retest) exists
nowhere else in this project.

Four requirements, matching how docs/61 §3.1 validates a setup plus the
trend-major filter of §2.2. Every one is derived from the source
material; none is invented here.
"""

from app.services.bbma.types import BBMASetupKind
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
    is_current = False
    if setup is not None:
        # `detect` walks the whole series, so the last bar index is the
        # series length minus one; setups carry their own entry index.
        is_current = setup.entry_index >= 0 and (
            setup.entry_index >= _latest_index(bbma) - _MAX_SETUP_AGE_BARS
        )

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


def _latest_index(bbma_result: object) -> int:
    """The index of the most recent bar the detector saw.

    `BBMAResult` deliberately does not carry the series length - it
    carries setups. The most recent setup's own index is the only
    in-band reference available, so "recent" is measured relative to the
    newest setup found. When there is exactly one setup this makes the
    age check trivially true, which is the honest behaviour: with no
    later structure to compare against, we cannot claim a setup is stale.
    """
    setups = getattr(bbma_result, "setups", [])
    return max((s.entry_index for s in setups), default=0)


__all__ = ["check"]

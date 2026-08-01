"""Deterministic economic-event filter (docs/12 §8, docs/48 §5). Reuses
`EconomicEventEvidence.risk_window`/`.importance` directly (Phase 5B) -
no new economic classification is invented here."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.models.enums import EconomicEventImportance
from app.services.economic_calendar.types import EconomicEventEvidence

_HIGH_SCORE_CAP = 4.0
_MEDIUM_SCORE_CAP = 7.0
_NO_EVENT_SCORE = 10.0


@dataclass(frozen=True, slots=True)
class EconomicFilterResult:
    economic_score: float
    hard_reject: bool
    reason: str | None


def analyze(events: Sequence[EconomicEventEvidence]) -> EconomicFilterResult:
    critical_in_window = next(
        (e for e in events if e.importance is EconomicEventImportance.CRITICAL and e.risk_window),
        None,
    )
    if critical_in_window is not None:
        return EconomicFilterResult(
            economic_score=0.0,
            hard_reject=True,
            reason=f"Critical economic event within risk window: {critical_in_window.event_name}",
        )

    high_in_window = any(
        e.importance is EconomicEventImportance.HIGH and e.risk_window for e in events
    )
    if high_in_window:
        return EconomicFilterResult(economic_score=_HIGH_SCORE_CAP, hard_reject=False, reason=None)

    medium_present = any(e.importance is EconomicEventImportance.MEDIUM for e in events)
    if medium_present:
        return EconomicFilterResult(
            economic_score=_MEDIUM_SCORE_CAP, hard_reject=False, reason=None
        )

    return EconomicFilterResult(economic_score=_NO_EVENT_SCORE, hard_reject=False, reason=None)

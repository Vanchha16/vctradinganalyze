"""Deterministic rejection and ranking (docs/17 §15/§16, docs/49 §8,
ADR-076). A strategy is rejected if its Market Match is 0 (regime-
incompatible) OR its total score falls below 50 (regime-compatible but
weak overall). Ties broken by `StrategyName`'s declaration order."""

from app.services.strategy.types import (
    RankedStrategy,
    RejectedStrategy,
    StrategyBreakdown,
    StrategyName,
)

_MINIMUM_TOTAL_SCORE = 50.0


def rejection_reason(strategy: StrategyName, breakdown: StrategyBreakdown) -> str | None:
    if breakdown.market_match == 0:
        return f"Current market regime is incompatible with {strategy.value}."
    if breakdown.total < _MINIMUM_TOTAL_SCORE:
        return (
            f"Total score {breakdown.total:.0f} is below the minimum threshold of "
            f"{_MINIMUM_TOTAL_SCORE:.0f}."
        )
    return None


def rank(
    scores: dict[StrategyName, StrategyBreakdown],
) -> tuple[
    StrategyName | None, StrategyBreakdown | None, list[RankedStrategy], list[RejectedStrategy]
]:
    """Returns `(primary_strategy, primary_breakdown, alternatives, rejected)`."""
    declaration_order = list(StrategyName)

    accepted: list[tuple[StrategyName, StrategyBreakdown]] = []
    rejected: list[RejectedStrategy] = []

    for strategy in declaration_order:
        breakdown = scores[strategy]
        reason = rejection_reason(strategy, breakdown)
        if reason is not None:
            rejected.append(
                RejectedStrategy(strategy=strategy, score=breakdown.total, reason=reason)
            )
        else:
            accepted.append((strategy, breakdown))

    accepted.sort(key=lambda pair: (-pair[1].total, declaration_order.index(pair[0])))

    if not accepted:
        return None, None, [], rejected

    primary_strategy, primary_breakdown = accepted[0]
    alternatives = [
        RankedStrategy(strategy=strategy, score=breakdown.total)
        for strategy, breakdown in accepted[1:]
    ]
    return primary_strategy, primary_breakdown, alternatives, rejected

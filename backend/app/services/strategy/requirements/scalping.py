"""Scalping requirements checklist (docs/17 §12, docs/49 §5). High
liquidity, fast momentum, no high-impact news - reuses
`risk_management`'s `liquidity_filter`/`economic_filter` directly
(ADR-071). Low Spread is excluded (no data source, ADR-074)."""

from app.services.risk_management.types import LiquidityClassification
from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle

_HIGH_LIQUIDITY = frozenset({LiquidityClassification.HIGH, LiquidityClassification.EXCELLENT})


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    high_liquidity = evidence.liquidity in _HIGH_LIQUIDITY

    fast_momentum = (
        evidence.technical is not None and evidence.technical.momentum.momentum is not None
    )

    no_high_impact_news = (
        not evidence.economic.hard_reject and evidence.economic.economic_score >= 7.0
    )

    met_count = sum([high_liquidity, fast_momentum, no_high_impact_news])
    return RequirementsResult(met_count=met_count, total_count=3)

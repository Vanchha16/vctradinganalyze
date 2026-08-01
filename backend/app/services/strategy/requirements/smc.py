"""SMC strategy requirements checklist (docs/17 §8, docs/49 §5). Order
Block/BOS/CHOCH/Liquidity Sweep/FVG presence - an exact 1:1 match to
`SMCAnalysisResult`'s own fields, no new detection logic."""

from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    if evidence.smc is None:
        return RequirementsResult(met_count=0, total_count=5)

    smc = evidence.smc
    checks = [
        len(smc.order_blocks) > 0,
        len(smc.bos) > 0,
        len(smc.choch) > 0,
        len(smc.liquidity_sweeps) > 0,
        len(smc.fair_value_gaps) > 0,
    ]
    return RequirementsResult(met_count=sum(checks), total_count=5)

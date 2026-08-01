"""Deterministic evidence-bullet extraction (docs/50 §6). No string
parsing of LLM output, no invention - every bullet traces to an
already-typed field on the `AnalysisContext`."""

from dataclasses import dataclass

from app.services.market_regime.types import VolatilityRegimeState

from .types import AnalysisContext


@dataclass(frozen=True, slots=True)
class ExtractedEvidence:
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    risks: list[str]


def extract(context: AnalysisContext) -> ExtractedEvidence:
    return ExtractedEvidence(
        supporting_evidence=_supporting_evidence(context),
        conflicting_evidence=_conflicting_evidence(context),
        risks=_risks(context),
    )


def _supporting_evidence(context: AnalysisContext) -> list[str]:
    bullets: list[str] = []

    technical = context.confidence.technical
    if technical is not None:
        moving_average = technical.trend_evidence.moving_average
        if moving_average.bullish_alignment or moving_average.bearish_alignment:
            bullets.append(f"Technical Analysis trend: {technical.trend.value}, EMA aligned.")

    smc = context.confidence.smc
    if smc is not None and smc.order_blocks:
        bullets.append(f"{len(smc.order_blocks)} SMC order block(s) present.")
    if smc is not None and smc.bos:
        bullets.append("Break of Structure confirmed.")

    if context.strategy.primary_strategy is not None:
        bullets.append(f"Strategy Engine favors {context.strategy.primary_strategy.value}.")

    return bullets


def _conflicting_evidence(context: AnalysisContext) -> list[str]:
    bullets = [c.description for c in context.confidence.conflicts]
    if context.risk is not None:
        bullets.extend(context.risk.rejected_reasons)
    return bullets


def _risks(context: AnalysisContext) -> list[str]:
    bullets: list[str] = []
    if context.risk is not None:
        bullets.extend(context.risk.warnings)

    for event in context.economic.events:
        if event.risk_window:
            bullets.append(f"{event.event_name} ({event.currency}) is within its risk window.")

    if (
        context.confidence.market_regime is not None
        and context.confidence.market_regime.volatility.state is VolatilityRegimeState.EXTREME
    ):
        bullets.append("Volatility is extreme.")

    return bullets

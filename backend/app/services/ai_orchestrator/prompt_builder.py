"""Deterministic prompt construction (docs/50 §7, replaces docs/35's
skeleton with concrete content). The model is given the already-decided
recommendation/confidence/risk/prices and asked only to narrate them -
never to decide anything (ADR-078/079)."""

from datetime import datetime
from decimal import Decimal

from app.models.enums import Recommendation
from app.utils.time import as_aware_utc

from .types import AnalysisContext

PROMPT_VERSION = "1.0.0"

_MAX_SECTION_WORDS = 120
_MAX_TOKENS = 1200

SYSTEM_PROMPT = (
    "You are a professional financial market analyst writing for traders. "
    "Your tone is objective, evidence-based, and concise - no hype, no "
    "emotional language, no promises. You are given a market analysis that "
    "has ALREADY been decided by deterministic rules: the recommendation, "
    "confidence score, risk level, and any entry/stop-loss/take-profit "
    "prices are fixed facts, not something you decide or may change. Your "
    "only job is to explain, in your own words, why the evidence supports "
    "what has already been decided. Rules you must never break: only "
    "reference facts, numbers, and evidence explicitly given to you in the "
    "context below - never invent a price, indicator value, news item, "
    "economic event, or structural detail that isn't present. Never output "
    "a recommendation, confidence value, or price of your own - those "
    "fields are not part of your response. Respond only with the JSON "
    f"schema you are given, each section under {_MAX_SECTION_WORDS} words."
)

_REASONING_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "technical": {"type": "string"},
        "smc": {"type": "string"},
        "economic": {"type": "string"},
        "news": {"type": "string"},
        "risk": {"type": "string"},
        "conclusion": {"type": "string"},
    },
    "required": ["summary", "technical", "smc", "economic", "news", "risk", "conclusion"],
    "additionalProperties": False,
}


def reasoning_json_schema() -> dict[str, object]:
    return _REASONING_JSON_SCHEMA


def build_user_prompt(
    context: AnalysisContext,
    recommendation: Recommendation,
    reasons: list[str],
    supporting_evidence: list[str],
    conflicting_evidence: list[str],
    risks: list[str],
) -> str:
    lines: list[str] = [
        f"Asset: {context.asset.symbol}",
        f"Timeframe: {context.timeframe.value}",
        f"Decided recommendation: {recommendation.value.upper()}",
    ]
    if reasons:
        lines.append(f"Recommendation reasons: {'; '.join(reasons)}")
    confidence_level = context.confidence.confidence_level.value
    lines.append(f"Confidence: {context.confidence.overall_confidence:.0f} ({confidence_level})")

    if context.candidate_setup is not None:
        setup = context.candidate_setup
        lines.append(
            f"Candidate setup: direction={setup.direction.value}, entry={setup.entry_price}, "
            f"stop_loss={setup.stop_loss}, take_profit={setup.take_profit}"
        )
    if context.risk is not None:
        lines.append(
            f"Risk evaluation: approved={context.risk.approved}, "
            f"risk_level={context.risk.risk_level.value}, trade_quality={context.risk.tier.value}"
        )

    if context.confidence.technical is not None:
        lines.append(
            f"Technical Analysis: trend={context.confidence.technical.trend.value}, "
            f"strength={context.confidence.technical.strength.value}, "
            f"score={context.confidence.technical.technical_score:.0f}"
        )
    if context.confidence.smc is not None:
        lines.append(
            f"SMC: structure={context.confidence.smc.market_structure.state.value}, "
            f"score={context.confidence.smc.smc_score:.0f}"
        )
    if context.confidence.market_regime is not None:
        lines.append(f"Market Regime: {context.confidence.market_regime.regime.value}")

    if context.news.articles:
        headlines = "; ".join(a.headline for a in context.news.articles[:5])
        lines.append(f"Recent news headlines: {headlines}")
    else:
        lines.append("Recent news: none available.")

    if context.economic.events:
        events = "; ".join(f"{e.event_name} ({e.currency})" for e in context.economic.events[:5])
        lines.append(f"Upcoming/recent economic events: {events}")
    else:
        lines.append("Economic events: none in the current window.")

    #: ADR-152. Placed last and labelled explicitly, because without it
    #: the model answers about whatever happens to be inside the +24h
    #: window - a click on Thursday's CPI produced a paragraph about
    #: today's bond auction. Full details, not just a name: the release's
    #: forecast against its previous is the whole reason it matters.
    if context.focus_event is not None:
        lines.append(f"The reader is asking specifically about: {_focus_event_line(context)}")

    if context.strategy.primary_strategy is not None:
        lines.append(f"Strategy fit: {context.strategy.primary_strategy.value}")
    else:
        lines.append("Strategy fit: no viable strategy for current conditions.")

    lines.append(f"Supporting evidence: {'; '.join(supporting_evidence) or 'none'}")
    lines.append(f"Conflicting evidence: {'; '.join(conflicting_evidence) or 'none'}")
    lines.append(f"Risks: {'; '.join(risks) or 'none'}")

    return "\n".join(lines)


def _focus_event_line(context: AnalysisContext) -> str:
    """One dense line describing the release the reader clicked."""
    event = context.focus_event
    assert event is not None  # guarded by the caller

    parts = [
        f"{event.event_name} ({event.currency}, {event.importance.value} importance)",
        f"releases {_relative_release(event.release_time, context.economic.calculated_at)}",
    ]
    if event.forecast is not None:
        forecast = f"forecast {_number(event.forecast)}{event.unit or ''}"
        if event.previous is not None:
            forecast += f" vs {_number(event.previous)}{event.unit or ''} previous"
        parts.append(forecast)
    elif event.previous is not None:
        parts.append(f"previous {_number(event.previous)}{event.unit or ''}")
    if event.actual is not None:
        parts.append(f"actual {_number(event.actual)}{event.unit or ''}")

    return (
        f"{', '.join(parts)}. Address this release directly in the `economic` section, "
        "including whether it lands near enough to matter for this setup. Do not change "
        "the recommendation because of it."
    )


def _relative_release(release_time: datetime, now: datetime) -> str:
    """"in 2 days" reads better than a timestamp, and tells the model the
    one thing it must judge: whether the release is close enough to
    matter for a setup on this timeframe."""
    # SQLite hands back naive datetimes where Postgres gives aware ones,
    # so normalise both - the same guard `risk_window.is_in_risk_window`
    # already applies to this exact column.
    delta = as_aware_utc(release_time) - as_aware_utc(now)
    hours = delta.total_seconds() / 3600
    if hours < -24:
        return f"{abs(round(hours / 24))} days ago"
    if hours < -1:
        return f"{abs(round(hours))} hours ago"
    if hours < 1:
        return "within the hour"
    if hours < 24:
        return f"in {round(hours)} hours"
    return f"in {round(hours / 24)} days"


def _number(value: Decimal) -> str:
    """Trims the Numeric(20, 8) trailing zeros so "0.4%" does not reach
    the model as "0.40000000" and burn tokens on noise."""
    return f"{value.normalize():f}"


def max_tokens() -> int:
    return _MAX_TOKENS

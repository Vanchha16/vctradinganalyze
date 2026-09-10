"""Deterministic prompt construction (docs/50 §7, replaces docs/35's
skeleton with concrete content). The model is given the already-decided
recommendation/confidence/risk/prices and asked only to narrate them -
never to decide anything (ADR-078/079)."""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from app.models.enums import Recommendation
from app.services.bbma.types import BBMAResult
from app.services.economic_calendar.types import EconomicEventEvidence
from app.services.smc.types import SMCAnalysisResult
from app.services.technical_analysis.types import TechnicalAnalysisResult
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
        lines.extend(_technical_lines(context.confidence.technical))
    if context.confidence.smc is not None:
        reference_price = (
            context.candidate_setup.entry_price if context.candidate_setup is not None else None
        )
        lines.extend(_smc_lines(context.confidence.smc, reference_price))
    if context.confidence.market_regime is not None:
        lines.append(f"Market Regime: {context.confidence.market_regime.regime.value}")

    if context.news.articles:
        lines.append("Recent news:")
        # Sentiment and importance, not just the headline: a bearish
        # headline the scorer rated low-importance means something
        # different from a high-importance one, and the model cannot
        # tell them apart from the text alone.
        lines.extend(
            f"  - [{a.sentiment.value}/{a.importance.value}] {a.headline}"
            for a in context.news.articles[:5]
        )
    else:
        lines.append("Recent news: none available.")

    if context.economic.events:
        lines.append("Economic events in window:")
        lines.extend(
            f"  - {_event_summary(e, context.economic.calculated_at)}"
            for e in context.economic.events[:6]
        )
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
        strategy_line = f"Strategy fit: {context.strategy.primary_strategy.value}"
        if context.strategy.strategy_score is not None:
            strategy_line += f" (score {context.strategy.strategy_score:.0f}/100)"
        # The runner-up matters: a narrow win means conditions suit two
        # approaches, which is worth saying out loud rather than
        # presenting the winner as obvious.
        if context.strategy.alternative_strategies:
            runner_up = context.strategy.alternative_strategies[0]
            strategy_line += f"; next best {runner_up.strategy.value} ({runner_up.score:.0f})"
        lines.append(strategy_line)
    else:
        lines.append("Strategy fit: no viable strategy for current conditions.")

    # ADR-158. BBMA is frequently the winning strategy, and until now the
    # model was told its name and score and nothing else - it could not
    # say why BBMA fired. Included whether or not BBMA won: a detected
    # setup is context even when another strategy scored higher.
    lines.extend(_bbma_lines(context.strategy.bbma))

    lines.append(f"Supporting evidence: {'; '.join(supporting_evidence) or 'none'}")
    lines.append(f"Conflicting evidence: {'; '.join(conflicting_evidence) or 'none'}")
    lines.append(f"Risks: {'; '.join(risks) or 'none'}")

    return "\n".join(lines)


def _bbma_lines(bbma: BBMAResult | None) -> list[str]:
    """BBMA structure in BBMA's own vocabulary (docs/61, ADR-158).

    The terms matter: an operator who reads BBMA expects "Extreme",
    "marked level", "retest", "trend major". Translating them into
    generic language would make the narration harder to check against a
    chart, not easier.
    """
    if bbma is None:
        return []

    setup = bbma.latest
    conditions = bbma.conditions
    if setup is None and conditions is None:
        return []

    lines = ["BBMA:"]

    if setup is not None:
        detail = (
            f"  {setup.kind.value} {setup.direction.value} setup - "
            f"entry {setup.entry_price:.2f} (MA5/10 band), "
            f"stop {setup.stop_loss:.2f}, target {setup.take_profit:.2f}"
        )
        if setup.marked_level is not None:
            detail += f"; marked level {setup.marked_level:.2f}"
        lines.append(detail)
        # The notes are what record that a reverse candle and a retest
        # were actually found - the difference between a real setup and
        # a shape that merely resembles one.
        lines.extend(f"  {note}" for note in setup.notes[:3])
    else:
        lines.append("  No completed setup - structure only.")

    if conditions is not None:
        flags = [
            name
            for name, present in (
                ("CSM", conditions.csm),
                ("CSAK", conditions.csak),
                ("CSK", conditions.csk),
                ("ZZL", conditions.zzl),
            )
            if present
        ]
        trend_major = (
            conditions.trend_major.value if conditions.trend_major is not None else "unknown"
        )
        band = "expanding" if conditions.bb_expanding else "flat"
        condition_line = f"  Trend major {trend_major}; Bollinger Bands {band}"
        if flags:
            condition_line += f"; {', '.join(flags)} present"
        lines.append(condition_line)

    return lines


def _technical_lines(technical: TechnicalAnalysisResult) -> list[str]:
    """Conclusions AND the numbers behind them (ADR-157).

    `trend=bullish, score=78` gives the model nothing to write about
    beyond restating it. RSI, ADX and the actual support/resistance
    prices are what let it say *why*, and they were already computed -
    fifteen indicators, discarded before the prompt.
    """
    lines = [
        f"Technical: trend={technical.trend.value}, strength={technical.strength.value}, "
        f"score={technical.technical_score:.0f}/100"
    ]

    evidence = technical.trend_evidence
    moving_average = evidence.moving_average
    if moving_average.bullish_alignment:
        alignment = "bullish"
    elif moving_average.bearish_alignment:
        alignment = "bearish"
    else:
        alignment = "mixed"
    lines.append(
        f"  ADX {evidence.adx:.0f} (DI+ {evidence.di_plus:.0f} / DI- {evidence.di_minus:.0f}); "
        f"EMA alignment {alignment}"
    )

    # A curated few, not the whole dict: OBV and stddev say little to a
    # reader, while RSI and ATR frame overbought/oversold and how much
    # room the stop actually has.
    for key, label in (("rsi_14", "RSI(14)"), ("cci_20", "CCI(20)"), ("atr_14", "ATR(14)")):
        value = technical.indicators.get(key)
        if value is not None:
            lines.append(f"  {label} {value:.2f}")

    if technical.support is not None:
        lines.append(f"  Support {technical.support.price} ({technical.support.source})")
    if technical.resistance is not None:
        lines.append(f"  Resistance {technical.resistance.price} ({technical.resistance.source})")

    return lines


def _smc_lines(smc: SMCAnalysisResult, reference_price: Decimal | None) -> list[str]:
    """SMC's zones carry prices; the state alone does not.

    Previously only `structure` and `score` reached the model, so it
    could never mention where an order block actually sits - the one
    thing an SMC reader wants.

    Zones are ranked by distance from the current price, not by the
    engine's own order. XAUUSD routinely has 40+ order blocks and the
    first three were 300 points away - technically true, useless to a
    reader deciding on a setup here and now.
    """
    lines = [
        f"SMC: structure={smc.market_structure.state.value}, score={smc.smc_score:.0f}/100"
    ]

    premium = smc.premium_discount
    lines.append(
        f"  Price is in {premium.position.value} of the "
        f"{premium.range_low}-{premium.range_high} range"
    )

    nearest_blocks = _nearest(
        smc.order_blocks, reference_price, lambda b: (b.zone_low, b.zone_high)
    )
    if nearest_blocks:
        blocks = "; ".join(
            f"{b.direction.value} {b.zone_low}-{b.zone_high}" for b in nearest_blocks[:3]
        )
        lines.append(f"  Nearest order blocks ({len(smc.order_blocks)} total): {blocks}")

    nearest_gaps = _nearest(smc.fair_value_gaps, reference_price, lambda g: (g.gap_low, g.gap_high))
    if nearest_gaps:
        gaps = "; ".join(
            f"{g.direction.value} {g.gap_low}-{g.gap_high}" for g in nearest_gaps[:2]
        )
        lines.append(f"  Nearest fair value gaps: {gaps}")
    if smc.liquidity_sweeps:
        lines.append(f"  Liquidity sweeps detected: {len(smc.liquidity_sweeps)}")

    return lines


def _nearest[T](
    zones: list[T], reference_price: Decimal | None, bounds: Callable[[T], tuple[Decimal, Decimal]]
) -> list[T]:
    """Closest-first by midpoint distance. With no reference price the
    engine's own order is kept rather than inventing one."""
    if reference_price is None:
        return list(zones)
    def distance(zone: T) -> Decimal:
        low, high = bounds(zone)
        return abs(((low + high) / 2) - reference_price)

    return sorted(zones, key=distance)


def _event_summary(event: EconomicEventEvidence, now: datetime) -> str:
    """Importance and timing, not just a name.

    "CPI m/m (USD)" and "CPI m/m (USD, critical, in 2 hours, forecast
    0.4% vs 0.1% previous)" support very different sentences, and every
    one of those fields was already on the object.
    """
    parts = [f"{event.event_name} ({event.currency}, {event.importance.value})"]
    parts.append(_relative_release(event.release_time, now))
    if event.forecast is not None:
        figure = f"forecast {_number(event.forecast)}{event.unit or ''}"
        if event.previous is not None:
            figure += f" vs {_number(event.previous)}{event.unit or ''} prev"
        parts.append(figure)
    if event.actual is not None:
        parts.append(f"actual {_number(event.actual)}{event.unit or ''}")
    return ", ".join(parts)


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

from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import Recommendation, Timeframe
from app.services.ai_orchestrator import prompt_builder
from app.services.ai_orchestrator.types import CandidateSetup
from app.services.risk_management.types import TradeDirection
from app.services.technical_analysis.types import TrendDirection
from tests.ai_orchestrator_helpers import (
    make_analysis_context,
    make_confidence_result,
    make_economic_event_evidence,
)


def test_prompt_version_is_set() -> None:
    assert prompt_builder.PROMPT_VERSION == "1.1.0"


def _setup(direction: TradeDirection) -> CandidateSetup:
    return CandidateSetup(
        direction=direction,
        entry_price=Decimal("4360.72"),
        stop_loss=Decimal("4392.15"),
        take_profit=Decimal("4297.86"),
    )


def _line(prompt: str, label: str) -> str:
    return next(line for line in prompt.splitlines() if line.strip().startswith(f"{label}:"))


def test_higher_timeframes_reach_the_prompt_with_their_agreement() -> None:
    """ADR-165 - a SELL against a bullish daily trend is the risk a reader
    most needs to hear, and the one a model skips when left implicit."""
    context = make_analysis_context(
        candidate_setup=_setup(TradeDirection.SHORT),
        higher_timeframes=[
            make_confidence_result(timeframe=Timeframe.H4, trend=TrendDirection.BEARISH),
            make_confidence_result(timeframe=Timeframe.D1, trend=TrendDirection.BULLISH),
        ],
    )

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "Higher timeframes:" in prompt
    assert "trend bearish" in _line(prompt, "H4")
    assert _line(prompt, "H4").endswith("agrees with the setup")
    assert _line(prompt, "D1").endswith("OPPOSES the setup")


def test_a_sideways_higher_timeframe_is_neutral_not_opposed() -> None:
    context = make_analysis_context(
        candidate_setup=_setup(TradeDirection.LONG),
        higher_timeframes=[
            make_confidence_result(timeframe=Timeframe.H4, trend=TrendDirection.SIDEWAYS)
        ],
    )

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert _line(prompt, "H4").endswith("neutral to the setup")


def test_a_higher_timeframe_without_data_says_so() -> None:
    """D1 has only weeks of history. Silence would read as "nothing to
    report", which is a different claim from "no data"."""
    context = make_analysis_context(
        higher_timeframes=[
            make_confidence_result(
                timeframe=Timeframe.D1,
                include_technical=False,
                include_smc=False,
                include_regime=False,
            )
        ]
    )

    prompt = prompt_builder.build_user_prompt(context, Recommendation.WAIT, [], [], [], [])

    assert "D1: no data available" in prompt


def test_without_a_setup_there_is_no_agreement_verdict() -> None:
    """WAIT has no direction, so "agrees" or "opposes" would be invented."""
    context = make_analysis_context(
        higher_timeframes=[make_confidence_result(timeframe=Timeframe.H4)]
    )

    prompt = prompt_builder.build_user_prompt(context, Recommendation.WAIT, [], [], [], [])

    assert "Higher timeframes:" in prompt
    assert "the setup" not in _line(prompt, "H4")


def test_no_higher_timeframe_section_when_none_were_analysed() -> None:
    context = make_analysis_context()

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "Higher timeframes:" not in prompt


def test_system_prompt_asks_the_model_to_address_higher_timeframes() -> None:
    assert "higher-timeframe" in prompt_builder.SYSTEM_PROMPT


def test_system_prompt_forbids_inventing_and_deciding() -> None:
    prompt = prompt_builder.SYSTEM_PROMPT
    assert "never" in prompt.lower()
    assert "invent" in prompt.lower()
    assert "already been decided" in prompt.lower() or "already" in prompt.lower()


def test_reasoning_json_schema_has_seven_required_sections() -> None:
    schema = prompt_builder.reasoning_json_schema()
    required = schema["required"]
    assert set(required) == {
        "summary",
        "technical",
        "smc",
        "economic",
        "news",
        "risk",
        "conclusion",
    }
    assert schema["additionalProperties"] is False


def test_build_user_prompt_includes_decided_recommendation() -> None:
    context = make_analysis_context()
    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])
    assert "Decided recommendation: BUY" in prompt
    assert "EURUSD" in prompt


def test_build_user_prompt_includes_reasons_when_present() -> None:
    context = make_analysis_context()
    prompt = prompt_builder.build_user_prompt(
        context, Recommendation.WAIT, ["No viable strategy."], [], [], []
    )
    assert "No viable strategy." in prompt


def test_build_user_prompt_handles_no_news_or_economic_events() -> None:
    context = make_analysis_context()
    prompt = prompt_builder.build_user_prompt(context, Recommendation.WAIT, [], [], [], [])
    assert "Recent news: none available." in prompt
    assert "Economic events: none in the current window." in prompt


def test_max_tokens_is_positive() -> None:
    assert prompt_builder.max_tokens() > 0


def test_focus_event_is_named_in_the_prompt() -> None:
    """ADR-152 - without this the model answers about whatever falls
    inside the default +24h window. A click on Thursday's CPI produced a
    paragraph about that day's bond auction instead."""
    context = make_analysis_context(focus_event=make_economic_event_evidence())

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "asking specifically about" in prompt
    assert "Core CPI m/m" in prompt
    assert "critical importance" in prompt


def test_focus_event_carries_forecast_against_previous() -> None:
    """A release matters because of the gap between forecast and
    previous - the name alone gives the model nothing to reason from."""
    context = make_analysis_context(focus_event=make_economic_event_evidence())

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "forecast 0.4% vs 0.1% previous" in prompt


def test_focus_event_values_drop_their_stored_trailing_zeros() -> None:
    """Stored as Numeric(20, 8), so an unformatted "0.40000000" would
    reach the model and spend tokens on noise."""
    context = make_analysis_context(focus_event=make_economic_event_evidence())

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "0.40000000" not in prompt


def test_focus_event_says_how_far_away_the_release_is() -> None:
    """The model must be able to say whether the release is close enough
    to matter for this setup, which a bare timestamp does not convey."""
    context = make_analysis_context(
        focus_event=make_economic_event_evidence(
            release_time=datetime(2026, 1, 3, tzinfo=UTC),  # helper context is 2026-01-01
        )
    )

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "in 2 days" in prompt


def test_focus_event_still_forbids_changing_the_recommendation() -> None:
    """The recommendation stays deterministic (ADR-079). Naming an event
    the reader cares about must not become licence to re-decide."""
    context = make_analysis_context(focus_event=make_economic_event_evidence())

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "Do not change the recommendation" in prompt


def test_prompt_is_unchanged_when_no_focus_event_is_given() -> None:
    """Every other caller - the hourly signal worker included - passes no
    focus event and must get exactly the prompt it got before."""
    context = make_analysis_context()

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "asking specifically about" not in prompt


def test_a_released_event_reports_its_actual() -> None:
    context = make_analysis_context(
        focus_event=make_economic_event_evidence(actual=Decimal("0.60000000"))
    )

    prompt = prompt_builder.build_user_prompt(context, Recommendation.SELL, [], [], [], [])

    assert "actual 0.6%" in prompt


def test_technical_section_carries_the_numbers_not_just_the_verdict() -> None:
    """ADR-157 - "trend=bullish, score=78" gives the model nothing to
    write about beyond restating it. Fifteen indicators were already
    computed and thrown away before the prompt."""
    context = make_analysis_context()

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "ADX" in prompt
    assert "DI+" in prompt
    assert "RSI(14)" in prompt
    assert "EMA alignment" in prompt


def test_support_and_resistance_reach_the_model_as_prices() -> None:
    """A reader wants the level, not the fact that one exists."""
    context = make_analysis_context()

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "Support " in prompt
    assert "Resistance " in prompt


def test_economic_events_carry_importance_and_timing() -> None:
    """"CPI m/m (USD)" and "CPI m/m (USD, critical), in 2 hours, forecast
    0.4% vs 0.1% prev" support very different sentences, and every one of
    those fields was already on the object."""
    event = make_economic_event_evidence(
        event_name="CPI m/m", release_time=datetime(2026, 1, 1, 2, tzinfo=UTC)
    )
    context = make_analysis_context(economic_events=[event])

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "CPI m/m (USD, critical)" in prompt
    assert "forecast 0.4% vs 0.1% prev" in prompt


def test_strategy_line_reports_the_score_and_the_runner_up() -> None:
    """A narrow win means conditions suit two approaches - worth saying
    rather than presenting the winner as obvious."""
    context = make_analysis_context()

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "/100)" in prompt


def test_smc_zones_are_ranked_by_distance_from_price() -> None:
    """XAUUSD routinely has 40+ order blocks. Listing the engine's first
    three put zones 300 points away in front of the model - technically
    true, useless for a setup here and now."""
    from decimal import Decimal

    from app.services.ai_orchestrator.prompt_builder import _nearest

    zones = [(Decimal("100"), Decimal("110")), (Decimal("400"), Decimal("410"))]

    ordered = _nearest(zones, Decimal("405"), lambda z: z)

    assert ordered[0] == (Decimal("400"), Decimal("410"))


def test_zone_ranking_without_a_reference_price_keeps_engine_order() -> None:
    """No price means no basis for "nearest" - keep the engine's order
    rather than inventing one."""
    from decimal import Decimal

    from app.services.ai_orchestrator.prompt_builder import _nearest

    zones = [(Decimal("100"), Decimal("110")), (Decimal("400"), Decimal("410"))]

    assert _nearest(zones, None, lambda z: z) == zones


def test_bbma_structure_reaches_the_model() -> None:
    """ADR-158 - BBMA frequently wins strategy selection, and the prompt
    previously carried only its name and score. The model could say
    "strategy fit: bbma (91/100)" and nothing about why it fired."""
    from tests.strategy_helpers import make_bbma_result

    context = make_analysis_context(bbma=make_bbma_result())

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "BBMA:" in prompt
    assert "extreme" in prompt
    assert "marked level" in prompt


def test_bbma_conditions_use_bbma_vocabulary() -> None:
    """An operator who reads BBMA expects "trend major", "CSK", "ZZL".
    Translating those into generic language would make the narration
    harder to check against a chart, not easier."""
    from tests.strategy_helpers import make_bbma_result

    context = make_analysis_context(bbma=make_bbma_result())

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "Trend major" in prompt
    assert "Bollinger Bands" in prompt


def test_no_bbma_section_when_there_is_no_bbma_data() -> None:
    """`None` means there were no candles. An empty "BBMA:" heading would
    imply the detector ran and found nothing, which is a different claim."""
    context = make_analysis_context()

    prompt = prompt_builder.build_user_prompt(context, Recommendation.BUY, [], [], [], [])

    assert "BBMA:" not in prompt

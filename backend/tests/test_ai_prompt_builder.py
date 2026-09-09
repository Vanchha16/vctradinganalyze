from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import Recommendation
from app.services.ai_orchestrator import prompt_builder
from tests.ai_orchestrator_helpers import make_analysis_context, make_economic_event_evidence


def test_prompt_version_is_set() -> None:
    assert prompt_builder.PROMPT_VERSION == "1.0.0"


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

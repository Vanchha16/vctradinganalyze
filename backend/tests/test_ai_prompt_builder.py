from app.models.enums import Recommendation
from app.services.ai_orchestrator import prompt_builder
from tests.ai_orchestrator_helpers import make_analysis_context


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

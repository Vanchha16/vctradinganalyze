import json

import pytest

from app.services.ai_orchestrator.providers.exceptions import MalformedAIResponseError
from app.services.ai_orchestrator.response_parser import parse

_VALID = {
    "summary": "Summary text.",
    "technical": "Technical text.",
    "smc": "SMC text.",
    "economic": "Economic text.",
    "news": "News text.",
    "risk": "Risk text.",
    "conclusion": "Conclusion text.",
}


def test_parse_valid_json_returns_reasoning_sections() -> None:
    result = parse(json.dumps(_VALID))
    assert result.summary == "Summary text."
    assert result.conclusion == "Conclusion text."


def test_parse_raises_on_invalid_json() -> None:
    with pytest.raises(MalformedAIResponseError):
        parse("not json at all")


def test_parse_raises_on_non_object_json() -> None:
    with pytest.raises(MalformedAIResponseError):
        parse(json.dumps(["a", "list"]))


def test_parse_raises_on_missing_keys() -> None:
    incomplete = dict(_VALID)
    del incomplete["conclusion"]
    with pytest.raises(MalformedAIResponseError):
        parse(json.dumps(incomplete))


def test_parse_raises_on_empty_string_section() -> None:
    invalid = dict(_VALID)
    invalid["summary"] = "   "
    with pytest.raises(MalformedAIResponseError):
        parse(json.dumps(invalid))


def test_parse_raises_on_non_string_section() -> None:
    invalid = dict(_VALID)
    invalid["summary"] = 123  # type: ignore[assignment]
    with pytest.raises(MalformedAIResponseError):
        parse(json.dumps(invalid))


def test_parse_enforces_word_cap() -> None:
    long_text = dict(_VALID)
    long_text["summary"] = " ".join(["word"] * 200)
    result = parse(json.dumps(long_text))
    assert len(result.summary.split()) == 120  # capped at 120 words, "..." appended to the last
    assert result.summary.endswith("...")

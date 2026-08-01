"""Defensive parsing of provider responses into `ReasoningSections`
(docs/50 §9). OpenAI's structured-output mode should make malformed JSON
rare, but the provider can still misbehave - this module never trusts
the response blindly."""

import json

from .providers.exceptions import MalformedAIResponseError
from .types import ReasoningSections

_MAX_SECTION_WORDS = 120
_REQUIRED_KEYS = ("summary", "technical", "smc", "economic", "news", "risk", "conclusion")


def parse(raw_content: str) -> ReasoningSections:
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise MalformedAIResponseError(f"response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise MalformedAIResponseError("response JSON is not an object")

    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        raise MalformedAIResponseError(f"response is missing required keys: {missing}")

    values: dict[str, str] = {}
    for key in _REQUIRED_KEYS:
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise MalformedAIResponseError(f"section '{key}' is not a non-empty string")
        values[key] = _enforce_word_cap(value.strip())

    return ReasoningSections(
        summary=values["summary"],
        technical=values["technical"],
        smc=values["smc"],
        economic=values["economic"],
        news=values["news"],
        risk=values["risk"],
        conclusion=values["conclusion"],
    )


def _enforce_word_cap(text: str, max_words: int = _MAX_SECTION_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class AIGenerationRequest:
    """docs/50 §7 - the fully-assembled prompt, built by `prompt_builder.py`.
    Never contains anything the provider itself decides - system/user
    prompt text and the target JSON schema are all pre-built."""

    system_prompt: str
    user_prompt: str
    json_schema: dict[str, object]
    max_tokens: int


@dataclass(frozen=True, slots=True)
class AIGenerationResponse:
    """Raw provider output before parsing - `response_parser.py` is
    responsible for validating/parsing `raw_content` into
    `ReasoningSections`, not the provider itself."""

    raw_content: str
    model_name: str


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """One turn in a multi-turn conversation - docs/52 §3 (ADR-092)."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class AIChatRequest:
    """docs/52 §3 (ADR-092) - free-text, multi-turn, unlike
    `AIGenerationRequest`'s fixed system+user pair and forced JSON
    schema. Built by `app/services/ai_chat/chat_prompt_builder.py`."""

    messages: list[ChatTurn]
    max_tokens: int


@dataclass(frozen=True, slots=True)
class AIChatResponse:
    """Raw provider output before persistence - free text, no parsing
    step needed (unlike `AIGenerationResponse`, which feeds
    `response_parser.py`)."""

    content: str
    model_name: str


class AIProvider(Protocol):
    """Interface every AI provider implements (docs/50 §8, ADR-081;
    extended docs/52 §3, ADR-092). Mirrors
    `app.services.news.providers.base.NewsProvider`/
    `app.services.economic_calendar.providers.base.EconomicCalendarProvider`'s
    shape exactly - `AIOrchestratorEngine`/`AIChatEngine` depend only on
    this interface, never a concrete provider class."""

    name: str

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        """Raises `TransientAIProviderError` for retryable failures,
        `PermanentAIProviderError` (or a more specific subclass) for
        failures that should not be retried."""
        ...

    def generate_chat_reply(self, request: AIChatRequest) -> AIChatResponse:
        """Free-text conversational reply (docs/52 §3, ADR-092) - same
        error-raising contract as `generate()`."""
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not perform a real generation."""
        ...


__all__ = [
    "AIChatRequest",
    "AIChatResponse",
    "AIGenerationRequest",
    "AIGenerationResponse",
    "AIProvider",
    "ChatTurn",
]

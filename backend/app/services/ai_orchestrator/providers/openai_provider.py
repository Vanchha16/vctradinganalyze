"""OpenAI implementation of `AIProvider` (docs/50 §8, ADR-081; extended
docs/52 §3, ADR-092). Reuses
`app.services.news_sentiment.ai_summary_generator.AISummaryGenerator`'s
httpx-Client-with-injectable-`transport` pattern exactly, extended with
OpenAI's structured-output mode so the model is constrained to the
target JSON schema at generation time - unlike News's isolated summary
call, failures here raise (retry/fallback is the orchestrator's job,
ADR-081), never silently return `None`.

`generate()` (Phase 6A) and `generate_chat_reply()` (Phase 6C) share one
`httpx.Client` construction and one status-code-to-exception
classification (`_post_chat_completion`) - the same integration, same
settings, same error handling, two request shapes (ADR-092)."""

import httpx

from app.config import settings

from .base import AIChatRequest, AIChatResponse, AIGenerationRequest, AIGenerationResponse
from .exceptions import (
    AIProviderConfigurationError,
    PermanentAIProviderError,
    TransientAIProviderError,
)


class OpenAIProvider:
    """`transport` is exposed only so tests can inject
    `httpx.MockTransport` - production code never needs to pass it
    (mirrors `TwelveDataHttpClient`/`AISummaryGenerator`)."""

    name = "openai"

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        body = self._post_chat_completion(
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            max_tokens=request.max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "reasoning",
                    "strict": True,
                    "schema": request.json_schema,
                },
            },
        )
        content = self._extract_content(body)
        return AIGenerationResponse(raw_content=content, model_name=settings.openai_model)

    def generate_chat_reply(self, request: AIChatRequest) -> AIChatResponse:
        body = self._post_chat_completion(
            messages=[{"role": turn.role, "content": turn.content} for turn in request.messages],
            max_tokens=request.max_tokens,
            response_format=None,
        )
        content = self._extract_content(body)
        return AIChatResponse(content=content, model_name=settings.openai_model)

    def _post_chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        response_format: dict[str, object] | None,
    ) -> dict[str, object]:
        if not settings.openai_api_key:
            raise AIProviderConfigurationError(
                "openai is configured as an AI provider but OPENAI_API_KEY is not set"
            )

        payload: dict[str, object] = {
            "model": settings.openai_model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            with httpx.Client(
                base_url=settings.openai_base_url,
                timeout=settings.openai_timeout_seconds,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                transport=self._transport,
            ) as client:
                response = client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise TransientAIProviderError(f"openai request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise TransientAIProviderError(f"openai transport error: {exc}") from exc

        if response.status_code == 401:
            raise PermanentAIProviderError("openai rejected the configured API key")
        if response.status_code == 429 or response.status_code >= 500:
            raise TransientAIProviderError(f"openai returned {response.status_code}")
        if response.status_code >= 400:
            raise PermanentAIProviderError(f"openai returned {response.status_code}")

        try:
            result: dict[str, object] = response.json()
        except ValueError as exc:
            raise PermanentAIProviderError(
                f"openai returned an unparseable response: {exc}"
            ) from exc
        return result

    @staticmethod
    def _extract_content(body: dict[str, object]) -> str:
        try:
            choices = body["choices"]
            content: str = choices[0]["message"]["content"]  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise PermanentAIProviderError(
                f"openai returned an unparseable response: {exc}"
            ) from exc
        return content

    def health_check(self) -> bool:
        return bool(settings.openai_api_key)

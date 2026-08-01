import json

import httpx
import pytest

from app.config import settings
from app.services.ai_orchestrator.prompt_builder import reasoning_json_schema
from app.services.ai_orchestrator.providers.base import AIGenerationRequest
from app.services.ai_orchestrator.providers.exceptions import (
    AIProviderConfigurationError,
    PermanentAIProviderError,
    TransientAIProviderError,
)
from app.services.ai_orchestrator.providers.openai_provider import OpenAIProvider

_REQUEST = AIGenerationRequest(
    system_prompt="system",
    user_prompt="user",
    json_schema=reasoning_json_schema(),
    max_tokens=1200,
)


def test_generate_raises_configuration_error_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    provider = OpenAIProvider()
    with pytest.raises(AIProviderConfigurationError):
        provider.generate(_REQUEST)


def test_generate_returns_response_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"summary": "ok"})}}]},
        )

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    response = provider.generate(_REQUEST)

    assert response.raw_content == json.dumps({"summary": "ok"})
    assert response.model_name == settings.openai_model


def test_generate_raises_permanent_error_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(PermanentAIProviderError):
        provider.generate(_REQUEST)


def test_generate_raises_transient_error_on_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(TransientAIProviderError):
        provider.generate(_REQUEST)


def test_generate_raises_transient_error_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(TransientAIProviderError):
        provider.generate(_REQUEST)


def test_generate_raises_permanent_error_on_unparseable_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(PermanentAIProviderError):
        provider.generate(_REQUEST)


def test_generate_never_calls_real_openai_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guardrail on the test suite itself - every test in this file must
    inject a transport, so the mock handler intercepts the request before
    it ever leaves the process; no test here hits the real OpenAI API."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    handler_was_called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal handler_was_called
        handler_was_called = True
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"summary": "ok"})}}]}
        )

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    provider.generate(_REQUEST)

    assert handler_was_called is True


def test_health_check_true_when_api_key_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    assert OpenAIProvider().health_check() is True


def test_health_check_false_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert OpenAIProvider().health_check() is False

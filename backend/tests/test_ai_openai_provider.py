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


def test_generate_records_the_token_usage_the_api_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-149 - cost is `usage` as OpenAI billed it, never a local
    estimate, so the counts are read straight off the response body."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"summary": "ok"})}}],
                "usage": {"prompt_tokens": 3120, "completion_tokens": 480},
            },
        )

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    response = provider.generate(_REQUEST)

    assert response.input_tokens == 3120
    assert response.output_tokens == 480


def test_generate_leaves_token_usage_unset_when_the_api_omits_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`None` means "not reported" and must stay distinguishable from a
    genuine zero - a guessed number would corrupt any cost total built
    on this column."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"summary": "ok"})}}]},
        )

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    response = provider.generate(_REQUEST)

    assert response.input_tokens is None
    assert response.output_tokens is None


def test_generate_ignores_a_malformed_usage_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-integer count is unusable, but it must not cost us the
    narration itself - the analysis is what the caller asked for."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"summary": "ok"})}}],
                "usage": {"prompt_tokens": "3120", "completion_tokens": None},
            },
        )

    provider = OpenAIProvider(transport=httpx.MockTransport(handler))
    response = provider.generate(_REQUEST)

    assert response.raw_content == json.dumps({"summary": "ok"})
    assert response.input_tokens is None
    assert response.output_tokens is None


def _captured_payload(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Runs one generate() and returns the JSON body actually sent."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    sent: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"summary": "ok"})}}]}
        )

    OpenAIProvider(transport=httpx.MockTransport(handler)).generate(_REQUEST)
    return sent


def test_the_output_cap_is_sent_as_max_completion_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-160 - this reached production. `max_tokens` is rejected
    outright by the newer model families ("Unsupported parameter"), and
    no test asserted the payload shape, so switching the model produced a
    400 on every analysis with nothing failing beforehand."""
    payload = _captured_payload(monkeypatch)

    assert "max_completion_tokens" in payload
    assert "max_tokens" not in payload


def test_temperature_is_omitted_unless_explicitly_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The newer families accept only the default and 400 on any explicit
    value, so sending nothing is the only setting that works everywhere."""
    monkeypatch.setattr(settings, "openai_temperature", None)

    assert "temperature" not in _captured_payload(monkeypatch)


def test_a_configured_temperature_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Still available for a model that allows pinning it."""
    monkeypatch.setattr(settings, "openai_temperature", 0.2)

    assert _captured_payload(monkeypatch)["temperature"] == 0.2

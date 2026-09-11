import json
from dataclasses import replace

import httpx
import pytest

from app.config import settings
from app.models.enums import NewsCategory, NewsImportance, NewsSentimentLabel
from app.services.news_sentiment.ai_summary_generator import AISummaryGenerator
from app.services.news_sentiment.types import RawArticleClassification
from tests.news_sentiment_helpers import make_raw_article

_CLASSIFICATION = RawArticleClassification(
    category=NewsCategory.INFLATION,
    importance=NewsImportance.CRITICAL,
    sentiment=NewsSentimentLabel.BEARISH,
    confidence=80.0,
    reason="Matched 1 sentiment keyword(s): rate hike (score=-2.0).",
    affected_assets=["EURUSD"],
)


def _capturing(captured: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    return httpx.MockTransport(handler)


def test_articles_affecting_no_active_asset_are_never_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-164: summarizing every article was ~99% of all OpenAI requests,
    almost all of them for news no signal ever reads."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    captured: list[httpx.Request] = []
    generator = AISummaryGenerator(transport=_capturing(captured))

    result = generator.generate(make_raw_article(), replace(_CLASSIFICATION, affected_assets=[]))

    assert result is None
    assert captured == []


def test_request_uses_the_news_summary_model_and_adr_160_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This call had no payload test, which is how `gpt-6-astra` rejecting
    `temperature` turned every summary into a 400 unnoticed (ADR-164)."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_model", "gpt-6-astra")
    monkeypatch.setattr(settings, "news_summary_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "openai_temperature", None)
    captured: list[httpx.Request] = []
    generator = AISummaryGenerator(transport=_capturing(captured))

    generator.generate(make_raw_article(), _CLASSIFICATION)

    [request] = captured
    payload = json.loads(request.content)
    assert payload["model"] == "gpt-4o-mini"
    assert payload["max_completion_tokens"] == 400
    assert "max_tokens" not in payload
    assert "temperature" not in payload


def test_temperature_is_sent_only_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_temperature", 0.3)
    captured: list[httpx.Request] = []
    generator = AISummaryGenerator(transport=_capturing(captured))

    generator.generate(make_raw_article(), _CLASSIFICATION)

    assert json.loads(captured[0].content)["temperature"] == 0.3


def test_generate_returns_none_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    generator = AISummaryGenerator()

    result = generator.generate(make_raw_article(), _CLASSIFICATION)

    assert result is None


def test_generate_returns_summary_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Summary: CPI beat forecast."}}]},
        )

    generator = AISummaryGenerator(transport=httpx.MockTransport(handler))

    result = generator.generate(make_raw_article(), _CLASSIFICATION)

    assert result == "Summary: CPI beat forecast."


def test_generate_returns_none_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    generator = AISummaryGenerator(transport=httpx.MockTransport(handler))

    result = generator.generate(make_raw_article(), _CLASSIFICATION)

    assert result is None


def test_generate_never_calls_real_openai_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guardrail on the test suite itself - every test in this file must
    inject a transport, so the mock handler intercepts the request before
    it ever leaves the process; no test here hits the real OpenAI API in
    CI (docs/46 §11)."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    handler_was_called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal handler_was_called
        handler_was_called = True
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    generator = AISummaryGenerator(transport=httpx.MockTransport(handler))
    generator.generate(make_raw_article(), _CLASSIFICATION)

    assert handler_was_called is True


def test_generate_enforces_word_cap() -> None:
    from app.services.news_sentiment.ai_summary_generator import _enforce_word_cap

    long_text = " ".join(["word"] * 200)
    capped = _enforce_word_cap(long_text, max_words=150)
    assert len(capped.split()) == 150
    assert capped.endswith("...")

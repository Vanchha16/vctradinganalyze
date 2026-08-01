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

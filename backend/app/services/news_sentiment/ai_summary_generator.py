"""The News Sentiment Engine's *only* AI-touching module (docs/10 §9,
docs/46 §9, ADR-051). Generates a narrative summary via a chat-completion
call - never the sentiment label/confidence/category/importance/
affected_assets, which remain fully deterministic (`sentiment_scorer.py`
and friends).

Guardrails: must reference the source article, never invent facts/
quotes/numbers/forecasts not present in the article text, max 150 words
(enforced post-generation), and degrades gracefully to `None` on any
failure - ingestion never blocks on this call (docs/46 §3).
"""

import logging

import httpx

from app.config import settings
from app.services.news.providers.base import RawNewsArticle
from app.services.news_sentiment.types import RawArticleClassification

logger = logging.getLogger(__name__)

_MAX_WORDS = 150
_SYSTEM_PROMPT = (
    "You summarize financial news articles for traders. Rules you must "
    "never break: only use facts, numbers, and quotes present in the "
    "provided article text - never invent any of them. Reference the "
    "source article. Never issue a BUY/SELL/WAIT recommendation. Respond "
    "in under 150 words, and explicitly include: Summary, Market Impact, "
    "Affected Assets, Risk, Confidence."
)


class AISummaryGenerator:
    """Isolated OpenAI chat-completion wrapper. `transport` is exposed
    only so tests can inject `httpx.MockTransport` - production code
    never needs to pass it (mirrors `TwelveDataHttpClient`)."""

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def generate(
        self,
        article: RawNewsArticle,
        classification: RawArticleClassification,
    ) -> str | None:
        if not settings.openai_api_key:
            return None

        user_prompt = (
            f"Headline: {article.title}\n"
            f"Source: {article.source_name}\n"
            f"Summary: {article.summary or 'N/A'}\n"
            f"Content: {article.content or 'N/A'}\n"
            f"Deterministic sentiment: {classification.sentiment.value} "
            f"(confidence {classification.confidence:.0f})\n"
            f"Affected assets: {', '.join(classification.affected_assets) or 'none detected'}"
        )

        try:
            with httpx.Client(
                base_url=settings.openai_base_url,
                timeout=settings.openai_timeout_seconds,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                transport=self._transport,
            ) as client:
                response = client.post(
                    "/chat/completions",
                    json={
                        "model": settings.openai_model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                body = response.json()
                text: str = body["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.warning("AI summary generation failed, degrading gracefully: %s", exc)
            return None

        if not text:
            return None
        return _enforce_word_cap(text)


def _enforce_word_cap(text: str, max_words: int = _MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."

"""The News Sentiment Engine's *only* AI-touching module (docs/10 §9,
docs/46 §9, ADR-051). Generates a narrative summary via a chat-completion
call - never the sentiment label/confidence/category/importance/
affected_assets, which remain fully deterministic (`sentiment_scorer.py`
and friends).

Guardrails: must reference the source article, never invent facts/
quotes/numbers/forecasts not present in the article text, max 150 words
(enforced post-generation), and degrades gracefully to `None` on any
failure - ingestion never blocks on this call (docs/46 §3).

ADR-164: only articles that affect an active asset are summarized, with
their own model (`NEWS_SUMMARY_MODEL`), and the request uses ADR-160's
shape. Summarizing every ingested article was ~99% of all OpenAI requests
- about 2,000 a day, nearly all of them for articles no signal reads - and
once `OPENAI_MODEL` moved to a model that rejects `temperature`, every one
of them failed with a 400.
"""

import logging

import httpx

from app.config import settings
from app.services import credential_resolver
from app.services.news.providers.base import RawNewsArticle
from app.services.news_sentiment.types import RawArticleClassification

logger = logging.getLogger(__name__)

_MAX_WORDS = 150
#: Headroom over 150 words (~200 tokens) so the word cap, not the token
#: limit, is what trims a long answer - a token cut mid-sentence reads worse.
_MAX_COMPLETION_TOKENS = 400
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
        # ADR-164: `affected_assets` is detected against the *active* assets
        # only, so empty means no signal will ever read this article. Checked
        # before the key, so an irrelevant article costs no request at all.
        if not classification.affected_assets:
            return None
        if not credential_resolver.resolve("openai"):
            return None

        user_prompt = (
            f"Headline: {article.title}\n"
            f"Source: {article.source_name}\n"
            f"Summary: {article.summary or 'N/A'}\n"
            f"Content: {article.content or 'N/A'}\n"
            f"Deterministic sentiment: {classification.sentiment.value} "
            f"(confidence {classification.confidence:.0f})\n"
            f"Affected assets: {', '.join(classification.affected_assets)}"
        )

        payload: dict[str, object] = {
            # Its own setting, not `openai_model` - even though both default to
            # the same model: sharing one setting is how moving the narration
            # model (ADR-160) broke this call.
            "model": settings.news_summary_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            # ADR-160's shape: newer models reject `max_tokens` and any
            # explicit `temperature`; every model reachable accepts this.
            "max_completion_tokens": _MAX_COMPLETION_TOKENS,
        }
        if settings.openai_temperature is not None:
            payload["temperature"] = settings.openai_temperature

        try:
            with httpx.Client(
                base_url=settings.openai_base_url,
                timeout=settings.openai_timeout_seconds,
                headers={"Authorization": f"Bearer {credential_resolver.resolve("openai")}"},
                transport=self._transport,
            ) as client:
                response = client.post("/chat/completions", json=payload)
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

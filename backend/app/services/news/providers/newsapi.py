from datetime import datetime
from typing import NoReturn

import httpx

from app.services.news.providers.base import NewsProviderCapabilities, RawNewsArticle
from app.services.news.providers.exceptions import (
    PermanentNewsProviderError,
    TransientNewsProviderError,
)
from app.services.news.providers.newsapi_http import NewsApiHttpClient, NewsApiTransportError

_CAPABILITIES = NewsProviderCapabilities(
    supported_languages=frozenset({"en"}),
    # NewsAPI.org's free "Developer" plan only searches the last month
    # (docs/46 §8's `max_lookback_days` contract) and only returns
    # articles delayed ~24h - both are plan limitations, not a bug here.
    max_lookback_days=30,
    supports_push=False,
)

# Broad financial/macro coverage matching the categories the deterministic
# analyzers (category_classifier, importance_scorer) already know how to
# classify (docs/46 §5) - central bank policy, inflation/rates, equities,
# crypto, and general economic releases.
_QUERY = (
    '(forex OR "central bank" OR inflation OR "interest rate" OR "interest rates" '
    'OR stocks OR equities OR crypto OR bitcoin OR economy OR economic OR GDP)'
)


class NewsApiAuthenticationError(PermanentNewsProviderError):
    """NewsAPI.org rejected the API key (401)."""


class NewsApiRateLimitedError(TransientNewsProviderError):
    """NewsAPI.org's own rate limit was hit (429)."""


def _parse_datetime(value: str) -> datetime:
    """NewsAPI.org returns ISO 8601 with a trailing `Z`."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class NewsApiProvider:
    """NewsAPI.org implementation of `NewsProvider` (docs/46 §8)."""

    name = "newsapi"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = NewsApiHttpClient(
            base_url=base_url, api_key=api_key, timeout=timeout, transport=transport
        )

    def fetch_latest(self, since: datetime) -> list[RawNewsArticle]:
        params = {
            "q": _QUERY,
            "from": since.strftime("%Y-%m-%dT%H:%M:%S"),
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": "100",
        }

        try:
            status_code, body = self._http.get("/v2/everything", params)
        except NewsApiTransportError as exc:
            raise TransientNewsProviderError(f"newsapi: {exc}") from exc

        if status_code == 200 and body.get("status") == "ok":
            return self._parse_articles(body)

        self._raise_for_error(status_code, body)

    def _parse_articles(self, body: dict[str, object]) -> list[RawNewsArticle]:
        raw_articles = body.get("articles", [])
        if not isinstance(raw_articles, list):
            raw_articles = []

        articles: list[RawNewsArticle] = []
        for row in raw_articles:
            # Removed/paywalled articles NewsAPI still lists with placeholder content.
            if row.get("title") in (None, "[Removed]") or row.get("url") in (None, "[Removed]"):
                continue
            source = row.get("source") or {}
            articles.append(
                RawNewsArticle(
                    title=str(row["title"]),
                    url=str(row["url"]),
                    published_at=_parse_datetime(row["publishedAt"]),
                    source_name=str(source.get("name") or "NewsAPI"),
                    summary=row.get("description"),
                    content=row.get("content"),
                    language="en",
                )
            )
        return articles

    def _raise_for_error(self, status_code: int, body: dict[str, object]) -> NoReturn:
        message = str(body.get("message", f"HTTP {status_code}"))

        if status_code == 401:
            raise NewsApiAuthenticationError(f"newsapi: {message}")
        if status_code == 429:
            raise NewsApiRateLimitedError(f"newsapi: {message}")
        if status_code >= 500:
            raise TransientNewsProviderError(f"newsapi: {message}")
        raise PermanentNewsProviderError(f"newsapi: {message}")

    def health_check(self) -> bool:
        try:
            status_code, body = self._http.get(
                "/v2/everything", {"q": "markets", "pageSize": "1"}
            )
        except NewsApiTransportError:
            return False
        return status_code == 200 and body.get("status") == "ok"

    def capabilities(self) -> NewsProviderCapabilities:
        return _CAPABILITIES

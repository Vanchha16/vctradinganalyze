"""Deterministic duplicate detection (docs/46 §7, ADR-054). No ML/LLM/"AI
Hash" is used - two concrete checks, either of which marks a candidate as
a duplicate of an existing article."""

import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from app.models.news_article import NewsArticle
from app.services.news.providers.base import RawNewsArticle

_TITLE_SIMILARITY_THRESHOLD = 0.85
_TIME_WINDOW = timedelta(hours=6)
_TRACKING_PARAM_PREFIXES = ("utm_", "ref", "fbclid", "gclid")
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes for `DateTime(timezone=True)`
    columns even though they were written UTC-aware (BACKLOG.md §9) -
    mirrors `signal.status_resolver._as_aware_utc`. `existing.published_at`
    comes back from the DB (naive on SQLite); `candidate.published_at` is
    freshly constructed by a provider (already aware) - without this,
    calling the pipeline a second time against a non-empty table raises
    `TypeError: can't subtract offset-naive and offset-aware datetimes`
    the moment a duplicate-window comparison actually runs (found running
    `POST /admin/news`/`/admin/maintenance` twice in a row, Phase 7D-C)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def normalize_url(url: str) -> str:
    """Scheme-insensitive, tracking-parameter-stripped, trailing-slash-free
    normalization, used for exact-match dedup."""
    parts = urlsplit(url.lower())
    query_pairs = [
        pair
        for pair in parts.query.split("&")
        if pair and not pair.split("=", 1)[0].startswith(_TRACKING_PARAM_PREFIXES)
    ]
    path = parts.path.rstrip("/")
    normalized = urlunsplit(("", "", path, "&".join(query_pairs), ""))
    return f"{parts.netloc}{normalized}"


def _tokenize(title: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(title.lower()))


def title_similarity(title_a: str, title_b: str) -> float:
    """Jaccard similarity over lowercased, punctuation-stripped tokens."""
    tokens_a, tokens_b = _tokenize(title_a), _tokenize(title_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union


def is_duplicate(candidate: RawNewsArticle, existing_articles: Sequence[NewsArticle]) -> bool:
    """docs/46 §7: exact normalized-URL match, OR normalized-title
    similarity above threshold within a time window."""
    candidate_url = normalize_url(candidate.url)
    for existing in existing_articles:
        if normalize_url(existing.url) == candidate_url:
            return True
        if title_similarity(candidate.title, existing.title) >= _TITLE_SIMILARITY_THRESHOLD:
            candidate_published_at = _as_aware_utc(candidate.published_at)
            existing_published_at = _as_aware_utc(existing.published_at)
            if abs(candidate_published_at - existing_published_at) <= _TIME_WINDOW:
                return True
    return False

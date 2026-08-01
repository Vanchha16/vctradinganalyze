"""Deterministic importance scoring (docs/10 §8, docs/46 §5, ADR-055). A
floor-and-escalate rule table combining source tier, category, and
keyword-triggered escalation - first match wins. No ML involved."""

from app.models.enums import NewsCategory, NewsImportance, NewsSourceTier

_CRITICAL_TIER1_ONLY = {NewsCategory.CENTRAL_BANK, NewsCategory.BREAKING_NEWS}
_CRITICAL_TIER1_OR_2 = {
    NewsCategory.INFLATION,
    NewsCategory.EMPLOYMENT,
    NewsCategory.GDP,
    NewsCategory.INTEREST_RATES,
}
_HIGH_ANY_TIER = {
    NewsCategory.POLITICS,
    NewsCategory.WAR,
    NewsCategory.ENERGY,
    NewsCategory.REGULATION,
}
_MEDIUM_ANY_TIER = {
    NewsCategory.COMMODITIES,
    NewsCategory.CRYPTO,
    NewsCategory.CORPORATE_EARNINGS,
}


def score(category: NewsCategory, source_tier: NewsSourceTier) -> NewsImportance:
    if category in _CRITICAL_TIER1_ONLY and source_tier is NewsSourceTier.TIER_1:
        return NewsImportance.CRITICAL
    if category in _CRITICAL_TIER1_OR_2 and source_tier in (
        NewsSourceTier.TIER_1,
        NewsSourceTier.TIER_2,
    ):
        return NewsImportance.CRITICAL
    if category in _CRITICAL_TIER1_ONLY:
        return NewsImportance.HIGH
    if category in _HIGH_ANY_TIER:
        return NewsImportance.HIGH
    if category in _CRITICAL_TIER1_OR_2:
        return NewsImportance.MEDIUM
    if category in _MEDIUM_ANY_TIER:
        return NewsImportance.MEDIUM
    return NewsImportance.LOW

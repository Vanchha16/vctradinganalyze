import pytest

from app.models.enums import NewsCategory, NewsImportance, NewsSourceTier
from app.services.news_sentiment.importance_scorer import score


@pytest.mark.parametrize(
    ("category", "tier", "expected"),
    [
        # docs/10 §8 worked examples: FOMC/CPI -> Critical.
        (NewsCategory.CENTRAL_BANK, NewsSourceTier.TIER_1, NewsImportance.CRITICAL),
        (NewsCategory.INFLATION, NewsSourceTier.TIER_1, NewsImportance.CRITICAL),
        (NewsCategory.INFLATION, NewsSourceTier.TIER_2, NewsImportance.CRITICAL),
        (NewsCategory.EMPLOYMENT, NewsSourceTier.TIER_1, NewsImportance.CRITICAL),
        (NewsCategory.GDP, NewsSourceTier.TIER_2, NewsImportance.CRITICAL),
        # Central Bank from a lower-tier source degrades to High, not Critical.
        (NewsCategory.CENTRAL_BANK, NewsSourceTier.TIER_2, NewsImportance.HIGH),
        (NewsCategory.BREAKING_NEWS, NewsSourceTier.TIER_3, NewsImportance.HIGH),
        # docs/10 §8: PMI/Retail Sales/Consumer Confidence -> High (approximated
        # here by Politics/War/Energy/Regulation).
        (NewsCategory.POLITICS, NewsSourceTier.TIER_3, NewsImportance.HIGH),
        (NewsCategory.WAR, NewsSourceTier.TIER_1, NewsImportance.HIGH),
        # Macro-data categories from a Tier-3 source degrade to Medium.
        (NewsCategory.INFLATION, NewsSourceTier.TIER_3, NewsImportance.MEDIUM),
        (NewsCategory.EMPLOYMENT, NewsSourceTier.TIER_3, NewsImportance.MEDIUM),
        # docs/10 §8: Company Earnings -> Medium.
        (NewsCategory.CORPORATE_EARNINGS, NewsSourceTier.TIER_1, NewsImportance.MEDIUM),
        (NewsCategory.CRYPTO, NewsSourceTier.TIER_2, NewsImportance.MEDIUM),
        (NewsCategory.COMMODITIES, NewsSourceTier.TIER_3, NewsImportance.MEDIUM),
        # docs/10 §8: Minor Political News -> Low has no remaining category/tier
        # combination left to exercise here.
        (NewsCategory.REGULATION, NewsSourceTier.TIER_3, NewsImportance.HIGH),
    ],
)
def test_score_matches_rule_table(
    category: NewsCategory, tier: NewsSourceTier, expected: NewsImportance
) -> None:
    assert score(category, tier) == expected


def test_score_never_returns_ignore() -> None:
    """Ignore is a reserved enum value for future manual overrides - the
    deterministic scorer never emits it in Phase 5A (docs/46 §5)."""
    for category in NewsCategory:
        for tier in NewsSourceTier:
            assert score(category, tier) != NewsImportance.IGNORE

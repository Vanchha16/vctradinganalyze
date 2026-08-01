from enum import StrEnum


class NewsCategory(StrEnum):
    """News category (docs/10_NEWS_SENTIMENT_ENGINE.md §5)."""

    CENTRAL_BANK = "central_bank"
    INFLATION = "inflation"
    EMPLOYMENT = "employment"
    GDP = "gdp"
    INTEREST_RATES = "interest_rates"
    POLITICS = "politics"
    WAR = "war"
    ENERGY = "energy"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    REGULATION = "regulation"
    CORPORATE_EARNINGS = "corporate_earnings"
    BREAKING_NEWS = "breaking_news"

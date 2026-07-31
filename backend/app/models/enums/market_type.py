from enum import StrEnum


class MarketType(StrEnum):
    """Tradable market categories, per docs/01_REQUIREMENTS.md ("Forex, Gold, Crypto, Indices")."""

    FOREX = "forex"
    METAL = "metal"
    CRYPTO = "crypto"
    INDEX = "index"

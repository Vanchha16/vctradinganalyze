"""Deterministic affected-asset detection (docs/10 §7/§12, docs/46 §5).
Matches article text against known asset symbols and a small currency/
commodity alias table - no ML/LLM involved."""

from collections.abc import Sequence

from app.models.asset import Asset

# Common-name aliases per currency/commodity code, so "Gold Prices Slide"
# matches XAUUSD even though the article never spells out the symbol or
# the asset's full display name.
_CURRENCY_ALIASES: dict[str, tuple[str, ...]] = {
    "XAU": ("gold", "bullion"),
    "XAG": ("silver",),
    "BTC": ("bitcoin",),
    "ETH": ("ethereum",),
    "EUR": ("euro", "eurozone"),
    "USD": ("dollar", "greenback"),
    "GBP": ("pound sterling", "sterling"),
    "JPY": ("yen",),
}


def detect(text: str, assets: Sequence[Asset]) -> list[str]:
    text_upper = text.upper()
    text_lower = text.lower()
    matched: list[str] = []

    for asset in assets:
        if asset.symbol.upper() in text_upper:
            matched.append(asset.symbol)
            continue

        aliases = _CURRENCY_ALIASES.get((asset.base_currency or "").upper(), ())
        if any(alias in text_lower for alias in aliases):
            matched.append(asset.symbol)

    return matched

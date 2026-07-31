"""Symbol and timeframe translation for Twelve Data (docs/41).

Kept in its own module, separate from `twelve_data.py`'s HTTP/error-
handling concerns, per docs/06 §4's "one responsibility per module."
"""

from app.models.enums import Timeframe

#: docs/41 §4 - index symbols cannot be derived mechanically. Left empty
#: until an entry is verified against Twelve Data's own symbol catalog;
#: do not guess at index tickers here.
INDEX_SYMBOL_OVERRIDES: dict[str, str] = {}

#: Recognized 3-letter currency/metal/crypto codes the mechanical rule
#: (docs/41 §3) is allowed to split a symbol into. Deliberately an
#: allowlist, not a bare length check - a 6-character symbol like
#: "NAS100" would otherwise be mis-split into "NAS/100", a plausible-
#: looking but nonsensical pair. Extend this set as new FOREX/METAL/CRYPTO
#: assets are added; anything not covered here needs an explicit entry in
#: an override table instead (following the same pattern as
#: `INDEX_SYMBOL_OVERRIDES`), not a looser heuristic.
_KNOWN_CURRENCY_CODES = frozenset(
    {
        # Major/minor forex currencies
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CHF",
        "AUD",
        "NZD",
        "CAD",
        # Metals
        "XAU",
        "XAG",
        # Crypto (3-letter only - 4+ letter quote currencies like USDT
        # need an override entry, since the mechanical rule assumes two
        # equal-length halves)
        "BTC",
        "ETH",
    }
)

#: docs/41 §5 - confirmed against Twelve Data's documented `interval` values.
TIMEFRAME_TO_INTERVAL: dict[Timeframe, str] = {
    Timeframe.M1: "1min",
    Timeframe.M5: "5min",
    Timeframe.M15: "15min",
    Timeframe.M30: "30min",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1day",
    Timeframe.W1: "1week",
    Timeframe.MN: "1month",
}


def timeframe_to_interval(timeframe: Timeframe) -> str:
    return TIMEFRAME_TO_INTERVAL[timeframe]


def to_provider_symbol(symbol: str) -> str | None:
    """Translate a canonical symbol (docs/41 §1) to Twelve Data's format.

    Checks the index override table first, then falls back to the
    mechanical FOREX/METAL/CRYPTO rule (split into two 3-letter halves and
    join with `/`) - but only when *both* halves are recognized currency
    codes (`_KNOWN_CURRENCY_CODES`), not merely because the symbol happens
    to be 6 characters long. A bare length check would also match
    non-currency symbols like "NAS100" and mis-split them into a
    plausible-looking but wrong pair - see docs/41 §4. Returns `None` if
    neither applies - callers must treat that as an unmappable symbol
    (docs/41 §6), not attempt a further guess.
    """
    if symbol in INDEX_SYMBOL_OVERRIDES:
        return INDEX_SYMBOL_OVERRIDES[symbol]

    if len(symbol) == 6:
        base, quote = symbol[:3], symbol[3:]
        if base in _KNOWN_CURRENCY_CODES and quote in _KNOWN_CURRENCY_CODES:
            return f"{base}/{quote}"

    return None


def from_provider_symbol(provider_symbol: str) -> str:
    """Reverse of the mechanical rule - strips the `/` delimiter, e.g. for
    cross-checking a response's `meta.symbol` against the requested
    canonical symbol."""
    return provider_symbol.replace("/", "")

# Symbol Normalization

Version: 1.0

Status: Defines the project's canonical internal symbol representation, then how it maps to each integrated provider. Twelve Data (Phase 3B) is the first mapping documented here, not the only reason this document exists - the canonical representation section applies regardless of which providers come later.

---

# 1. Canonical Internal Representation

Every `Asset.symbol` in this project (docs/03 §5) is a **plain, uppercase, separator-free string** - the same convention already used throughout the codebase and its examples (`EURUSD`, `GBPUSD`, `XAUUSD`, `BTCUSD`, `US30`, `NAS100`). This is the *only* symbol format anything above the provider layer ever sees - `MarketDataService`, repositories, `IndicatorService`, and every indicator function all operate on this canonical form. No provider-specific format leaks past `app/services/market_data/providers/`.

Alongside `symbol`, every `Asset` carries:

- `market_type` (`MarketType`: `FOREX`, `METAL`, `CRYPTO`, `INDEX`)
- `base_currency` / `quote_currency` (nullable `str`) - populated for `FOREX`/`METAL`/`CRYPTO`, `None` for `INDEX` (an index isn't a currency pair)

This is deliberately minimal - it's what docs/03 already specifies, not a new schema. The rest of this document defines how to go from this canonical form to a specific provider's expected format, and back.

**Why a canonical form independent of any single provider**: providers disagree with each other on formatting (a forex pair might be `EUR/USD` to one provider and `EURUSD=X` to another), so the canonical form has to be provider-agnostic by construction, not just "whatever the first provider happens to use." docs/38 §3 and docs/40 §3 already established that translation is a *per-provider adapter concern* - this document is where the actual translation rules live, so they don't need re-deriving (or worse, silently duplicating with drift) every time a provider is added.

---

# 2. General Translation Strategy

For any provider, symbol translation is:

1. **An explicit override table** for symbols that don't follow a mechanical rule (almost always `INDEX` symbols - see §4) - checked first.
2. **A mechanical rule** for symbol classes that genuinely follow one (`FOREX`/`METAL`/`CRYPTO` - see §3) - checked if no override exists.
3. **A hard failure** (`PermanentProviderError`) if neither applies - a provider should never guess.

This is intentionally *not* a single generic function shared across providers - each provider's module owns its own translation (docs/40 §3), because "how to translate" (the override table, the mechanical rule's separator/order) is specific to that provider's actual conventions, even when the *shape* of the strategy (override-then-mechanical-then-fail) is shared.

---

# 3. Mechanical Rule: FOREX / METAL / CRYPTO

For any asset where `base_currency` and `quote_currency` are both set, the mechanical rule is: **insert the provider's pair delimiter between `base_currency` and `quote_currency`**. For Twelve Data, that delimiter is `/`:

| Canonical | market_type | base/quote | Twelve Data |
|---|---|---|---|
| `EURUSD` | FOREX | EUR / USD | `EUR/USD` |
| `GBPUSD` | FOREX | GBP / USD | `GBP/USD` |
| `XAUUSD` | METAL | XAU / USD | `XAU/USD` |
| `BTCUSD` | CRYPTO | BTC / USD | `BTC/USD` |

Reverse direction (Twelve Data → canonical, needed when parsing `meta.symbol` from a response for logging/validation): strip the delimiter and concatenate, i.e. `EUR/USD` → `EURUSD`.

This rule is confirmed correct against Twelve Data's own documented examples (forex: `CNY/JPY`; crypto: `BTC/ETH`; commodities: `XAU/USD`) - see sources at the end of this document.

**Implementation note (discovered during Phase 3B build, not just theoretical):** the mechanical rule must not be "split any 6-character symbol in half" - `NAS100` is also 6 characters and would mis-split into the plausible-looking but wrong pair `NAS/100`. `to_provider_symbol` (`app/services/market_data/providers/twelve_data_symbols.py`) therefore only applies the split when *both* halves are in a known-currency-code allowlist (`_KNOWN_CURRENCY_CODES`), not merely because the length matches. Extend that allowlist as new FOREX/METAL/CRYPTO assets are added; a symbol that doesn't fit the allowlist (e.g. a crypto pair quoted in `USDT`, a 4-letter code) needs its own override entry, the same way indices do (§4) - it should not widen the allowlist's length assumption.

---

# 4. Explicit Table: INDEX

Index tickers are **not** mechanically derivable - different data vendors use different conventions for the same index (e.g. the Dow Jones Industrial Average appears as `^DJI`, `DJI`, `.DJI`, or `DJIA` depending on the source), and public documentation review alone could not confirm Twelve Data's exact convention for the specific indices docs/03 §5 uses as examples. Do not guess at these - verify against Twelve Data's `/symbol_search` or `/indices` catalog endpoint before enabling an index in production.

| Canonical | Description | Twelve Data symbol | Verified? |
|---|---|---|---|
| `US30` | Dow Jones Industrial Average | *unconfirmed* | ❌ Confirm via `/symbol_search` before enabling |
| `NAS100` | Nasdaq 100 | *unconfirmed* | ❌ Confirm via `/symbol_search` before enabling |

**`TwelveDataProvider` must raise `PermanentProviderError` for any `INDEX` symbol not in this table** (§6) - it must never fall back to a guess. Update this table (and mark entries verified) as part of actually enabling index collection through Twelve Data; until then, only `FOREX`/`METAL`/`CRYPTO` assets should be configured for this provider in practice.

---

# 5. Timeframe Mapping

Confirmed against Twelve Data's documented `interval` parameter values:

| Canonical `Timeframe` | Twelve Data `interval` |
|---|---|
| `M1` | `1min` |
| `M5` | `5min` |
| `M15` | `15min` |
| `M30` | `30min` |
| `H1` | `1h` |
| `H4` | `4h` |
| `D1` | `1day` |
| `W1` | `1week` |
| `MN` | `1month` |

All 9 canonical timeframes have a direct equivalent - no gaps, no approximation needed (Twelve Data additionally offers `45min`, `2h`, `8h`, which the project has no canonical `Timeframe` for and therefore never requests).

---

# 6. Failure Mode

`TwelveDataProvider`'s symbol-mapping function raises `PermanentProviderError` (specifically, a `TwelveDataInvalidSymbolError` subclass - docs/40 §5) when a canonical symbol has no override entry and doesn't have both `base_currency`/`quote_currency` set for the mechanical rule to apply. This surfaces as a clear, non-retryable failure (`MarketDataService` moves on to the next provider, or logs+skips if none remain) rather than sending a malformed request to Twelve Data and burning rate-limited quota discovering it.

---

# 7. Other Data-Shape Notes

- **Volume**: Twelve Data forex responses commonly report `0` or omit volume entirely (forex is OTC, without a single consolidated volume figure) - `RawCandle.volume: float | None` already accommodates this; treat a `"0"` volume string from Twelve Data as `0.0`, not `None` (it's a reported value, just an uninformative one) - only a genuinely absent field maps to `None`.
- **Currency cross-check**: Twelve Data's response `meta.currency` can be compared against `Asset.quote_currency` as an extra sanity check (docs/34's "Currency" validation point) - not implemented as a hard rejection in Phase 3B, but worth logging a warning on mismatch since it would indicate a symbol-mapping bug.

---

Sources: [Twelve Data API Documentation](https://twelvedata.com/docs), [Getting historical data](https://support.twelvedata.com/en/articles/5214728-getting-historical-data), [How to find all available symbols at Twelve Data](https://support.twelvedata.com/en/articles/5620513-how-to-find-all-available-symbols-at-twelve-data)

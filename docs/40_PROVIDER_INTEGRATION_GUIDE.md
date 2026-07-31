# Provider Integration Guide

Version: 1.0

Status: The canonical, procedural checklist for integrating any market-data provider into the pipeline defined in docs/38_MARKET_DATA_ARCHITECTURE.md. Distinct from docs/38 (architecture) and docs/39 (indicator math) - this document is "what to do," not "how it's designed" or "what the numbers mean." Written during Phase 3.5, before any real provider is integrated, so Phase 3B (Twelve Data first) is "fill in this checklist" rather than re-deriving these decisions.

---

# 1. When to Use This Guide

Follow this checklist whenever adding a new `MarketDataProvider` implementation - Twelve Data (Phase 3B), any provider added after it, or a replacement if a provider is ever swapped out. None of these steps should require changing `MarketDataService`, the repositories, or the scheduler (docs/38 §10) - if a step seems to require that, stop and reconsider whether it's actually a `MarketDataProvider` concern or something that belongs in the orchestration layer instead.

---

# 2. Required Interface Methods

Implement `app.services.market_data.providers.base.MarketDataProvider`:

- `name: str` - a short, stable identifier (e.g. `"twelve_data"`), used in logs, settings keys, and rate-limit configuration.
- `get_candles(symbol, timeframe, start, end) -> list[RawCandle]` - see §3-§5.
- `health_check() -> bool` - a cheap liveness check. Prefer the provider's own lightweight status/ping endpoint if it has one; otherwise a minimal authenticated request. Must not raise - catch and return `False` on any failure.
- `capabilities() -> ProviderCapabilities` - see §6.

Do not implement rate limiting inside the provider. Wrap it in `RateLimitedProvider` at construction time instead (§8) - this keeps every provider's `get_candles` free of throttling logic and makes rate limiting testable once, generically.

---

# 3. Symbol Normalization

The canonical symbol is `Asset.symbol` (e.g. `EURUSD`, `XAUUSD`). Translate to/from the provider's own format entirely inside the provider module - e.g. a private `to_provider_symbol(symbol: str) -> str | None` function. Do not add a new database table for this unless the mapping genuinely can't be derived by a simple rule (see docs/38 §3 - still true as of Phase 3.5; revisit only if a provider actually requires it).

**Important (learned building the Twelve Data provider, Phase 3B):** `MarketDataProvider.get_candles` only receives a bare canonical symbol string - no `Asset`, no `market_type`. This means the mapping function cannot rely on knowing the asset class when deciding how to translate a symbol; a purely mechanical rule based on symbol *shape alone* (e.g. "split any 6-character symbol in half") is unsafe, because an unrelated symbol from a different asset class can accidentally match the same shape and get silently mis-translated into a plausible-looking but wrong provider symbol (see docs/41 §3's note on `NAS100` almost being split like a forex pair). Guard the mechanical rule with an allowlist of values it's actually meant to match (e.g. known currency codes), not just a length/format check - and see docs/41_SYMBOL_NORMALIZATION.md for the concrete pattern to follow.

---

# 4. Timeframe Mapping

Map every canonical `Timeframe` (`M1, M5, M15, M30, H1, H4, D1, W1, MN`) the provider actually supports to its native representation, entirely inside the provider module. Do not leak provider-specific timeframe strings past the provider boundary. If the provider doesn't support a given timeframe at all, it must not appear in that provider's `ProviderCapabilities.supported_timeframes` (§6) - `MarketDataService` will then never call `get_candles` for it, rather than the provider needing to reject it reactively.

---

# 5. Error Classification

Every failure inside `get_candles` must be raised as one of (or a provider-specific subclass of) the base categories in `app.services.market_data.exceptions`:

- `TransientProviderError` - worth retrying (timeouts, 5xx, rate-limit responses your provider didn't already avoid via `RateLimitedProvider`, temporary network errors).
- `PermanentProviderError` - not worth retrying (bad/expired API key, invalid symbol, malformed request). `UnsupportedTimeframeError` is a `PermanentProviderError` subclass, kept as a reactive fallback - `capabilities()` should make it unreachable in practice (§6).
- `ProviderConfigurationError` - the provider is misconfigured at setup time (missing required API key, invalid settings) - raise this from construction, not from `get_candles`.

**Provider-specific exceptions are encouraged** where they add real diagnostic value - e.g. `TwelveDataAuthenticationError(PermanentProviderError)` or `TwelveDataQuotaExceededError(TransientProviderError)` - as long as they subclass the correct base category, since `MarketDataService` only ever catches by base category (docs/38 §7-§8). Put provider-specific exceptions in the provider's own module, not in the shared `exceptions.py`.

Never let a raw HTTP-client exception (e.g. `httpx.HTTPError`) escape `get_candles` uncaught - translate it to one of the categories above so `MarketDataService`'s retry/failover logic can reason about it.

---

# 6. Capability Declaration

Return a `ProviderCapabilities` from `capabilities()`:

```python
ProviderCapabilities(
    supported_timeframes=frozenset({Timeframe.M1, Timeframe.H1, Timeframe.D1}),  # only what's actually supported
    supported_market_types=frozenset({MarketType.FOREX, MarketType.METAL}),      # None = no restriction
    max_lookback=timedelta(days=730),                                            # None = no known limit
)
```

`ProviderCapabilities` is a value object specifically so it can grow new fields (e.g. a future `max_symbols_per_request`) without breaking existing providers or requiring a signature change - new fields must have defaults. Compute this once (e.g. a module-level constant, as `MockMarketDataProvider` does) rather than rebuilding it on every call, unless the provider's real capabilities can change at runtime.

`MarketDataService` checks `capabilities().supports(timeframe, market_type=asset.market_type)` **before** calling `get_candles` - declare accurately, since an over-broad declaration wastes a real request (and rate-limit budget) discovering the failure reactively, while an over-narrow one needlessly skips a provider that could have served the request.

---

# 7. Rate-Limit Configuration

Add an entry to `settings.market_data_rate_limits_per_minute` for the new provider's `name`, set to its actual documented rate limit (check the provider's API docs - free tiers are often much lower than paid tiers). If omitted, `settings.market_data_default_rate_limit_per_minute` (60/minute) applies, which is almost certainly wrong for a real provider - don't rely on the default.

The factory (`app/dependencies/market_data.py::get_market_data_providers`) wraps every provider in `RateLimitedProvider` automatically - no per-provider code needed here beyond the settings entry.

---

# 8. Secrets and Configuration Convention

- API keys: add `<PROVIDER_NAME>_API_KEY` to `.env.example` (blank placeholder) and `Settings` (e.g. `twelve_data_api_key: str = ""`), following the existing `NEWS_API_KEY`/`ECONOMIC_API_KEY` precedent (docs/06 §14).
- Never hardcode a key, base URL, or other environment-specific value (ADR-017) - everything configurable through `Settings`.
- Never log a key or raw request/response containing one - the shared `structlog` redaction (`_redact_sensitive_keys`, `app/core/logging.py`) already redacts common key names (`token`, `secret`, `api_key`), but double-check a provider-specific field name isn't missed if it doesn't match those patterns.
- Add the provider's name to `settings.market_data_providers` to activate it; leaving it out of that list means it's implemented but not wired in, which is useful for merging provider code ahead of actually enabling it.

---

# 9. Health-Check Integration

`GET /health/ready` already reports every configured provider's `health_check()` result diagnostically (Phase 3.5) - no route changes are needed when adding a provider, it's picked up automatically via `get_market_data_providers()`.

---

# 10. Testing Requirements

- **Contract test (mandatory)**: call `tests.market_data_contract.assert_provider_contract(provider, symbol, timeframe, start, end)` against the new provider, using a symbol/timeframe its `capabilities()` claims to support. See `test_mock_provider.py::test_mock_provider_satisfies_provider_contract` for the reference usage.
- **No real API calls in the standard test run.** Record a representative response as a fixture (e.g. `tests/fixtures/market_data/<provider_name>/<scenario>.json`) and have the provider test read from it via a mocked HTTP client - do not let `pytest` (or CI) make live calls to a real provider, which would be slow, flaky, and burn real rate-limit quota on every run.
- **Error classification tests**: at least one test per exception category the provider can raise (§5), confirming the right base category is used - this is what lets `MarketDataService`'s retry/failover behave correctly without needing provider-specific knowledge.
- **Symbol/timeframe mapping tests**: verify the canonical-to-provider-native translation in both directions where applicable, independent of any HTTP call.
- Follow the existing repo convention: tests live in `backend/tests/`, one file per concern (e.g. `test_twelve_data_provider.py`), verified with the full suite (`ruff check .`, `mypy app`, `pytest -q`) before considering the integration complete - the same bar every phase in this project has been held to.

---

# 11. Wiring Checklist Summary

1. Implement `MarketDataProvider` in `app/services/market_data/providers/<name>.py` (§2-§6).
2. Add provider-specific exceptions in that same module if needed (§5).
3. Add `<name>` to `_PROVIDER_FACTORIES` in `app/dependencies/market_data.py`.
4. Add `<name>` to `settings.market_data_providers` and a real rate limit to `settings.market_data_rate_limits_per_minute` (§7).
5. Add `<PROVIDER_NAME>_API_KEY` (or equivalent) to `.env.example` and `Settings` (§8).
6. Write the contract test, fixture-based tests, error-classification tests, and mapping tests (§10).
7. Run the full verification suite (`ruff`, `mypy`, `pytest`, and the CI Postgres migration check if the change touches models/migrations).
8. If any decision here was inferred rather than explicit in the provider's own docs, record it as a new ADR (see ADR-022/023/024 for the established pattern) and update BACKLOG.md.

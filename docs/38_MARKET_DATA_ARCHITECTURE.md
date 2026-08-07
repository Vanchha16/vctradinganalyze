# Market Data Architecture

Version: 1.0

Status: Defines Phase 3A (Market Data Foundation - provider abstraction + `MockMarketDataProvider`, no external API). Phase 3B (real provider integration, starting with Twelve Data) attaches to this architecture without changing the service layer.

---

# 1. Scope

Phase 3 is split into two sub-phases (see docs/30 Phase 3, BACKLOG.md):

- **Phase 3A - Market Data Foundation**: provider abstraction, `MarketDataService`, `Asset`/`Candle` models, timeframe/symbol handling, repositories, scheduler interface, and a `MockMarketDataProvider` that generates synthetic OHLCV data. No external API integration.
- **Phase 3B - Real Provider Integration**: adds a real provider (Twelve Data first), implementing the same `MarketDataProvider` interface defined here. The architecture must allow additional providers to be added later without changing `MarketDataService` or anything above it.

This document defines the architecture both sub-phases are built against. It does not cover indicator synthesis, trend detection, or technical scoring (docs/08 §7-11) - that remains Phase 4's Technical Analysis Engine, consuming the `indicator_results` this phase populates.

---

# 2. Provider Abstraction

A `MarketDataProvider` is an interface (Python `Protocol` or ABC in `app/services/market_data/providers/base.py`), not a concrete class services depend on directly.

Required operations:

- `name` - a short identifier (e.g. `"mock"`, `"twelve_data"`), used in logging and health-check reporting.
- `get_candles(symbol: str, timeframe: Timeframe, start: datetime, end: datetime) -> list[RawCandle]` - fetch OHLCV data for a canonical symbol/timeframe over a UTC time range. Returns provider-native data already mapped through this provider's symbol/timeframe adapters (§3, §4) but not yet normalized/validated (§5) - that step is the caller's (`MarketDataService`'s) responsibility, so normalization logic lives in one place, not duplicated per provider.
- `health_check() -> bool` - a cheap liveness check (e.g. a lightweight endpoint call, or `True` unconditionally for `MockMarketDataProvider`).

`MarketDataService` (in `app/services/market_data_service.py`) depends only on this interface - never on a concrete provider class - per docs/06 §5 (constructor injection, never instantiate dependencies inside a service). Which provider(s) it receives is a wiring concern (§9 Provider Lifecycle), not something the service decides for itself.

---

# 3. Symbol Normalization

The canonical symbol is `Asset.symbol` as stored in the database (e.g. `EURUSD`, `XAUUSD`, `BTCUSD`, `US30`) - matching the examples in docs/03 §5. Every provider is responsible for translating between this canonical symbol and its own symbol format (e.g. a future provider might need `EUR/USD` or `EURUSD:CUR`).

This translation is a per-provider adapter concern (a small mapping function/table inside each provider implementation), not a new database table. A persisted `provider_symbol_map` table is deferred (see BACKLOG.md) - not needed while only one provider (Mock, then Twelve Data) exists per asset; revisit if a future provider needs it and the mapping can't be derived by a simple rule (e.g. inserting a `/`).

`MockMarketDataProvider` uses the canonical symbol unchanged (no translation needed, since it doesn't call an external API).

---

# 4. Timeframe Mapping

Canonical timeframes (`app/models/enums.py::Timeframe`), matching docs/08 §4 exactly:

`M1, M5, M15, M30, H1, H4, D1, W1, MN`

Every provider maps canonical timeframes to its own representation internally (e.g. a future provider might expect `"1min"`, `"1day"`). `MarketDataService` and every layer above it only ever deals in the canonical `Timeframe` enum - provider-specific strings never leak past the provider's own module.

Not every provider necessarily supports every timeframe. A provider that lacks a mapping for a requested timeframe raises a clear, typed error (`UnsupportedTimeframeError` or similar) rather than silently returning wrong data - `MarketDataService` decides whether to fail or fall back to another provider (§8).

---

# 5. Data Normalization

Raw provider data is converted to a validated `Candle` (Pydantic or a plain dataclass, not yet the ORM model) before persistence, enforcing docs/08 §12's validation rules:

- Timestamp is UTC-aware (naive timestamps from a provider are assumed to be UTC and made aware, then converted if the provider documents a different source timezone - not currently expected, but the conversion point exists here so it isn't scattered).
- OHLC values are all present and numeric (`Decimal`, not `float`, to avoid floating-point drift in price data).
- `high >= low`, `high >= open`, `high >= close`, `low <= open`, `low <= close` - corrupted OHLC is rejected, not silently accepted (docs/08 §12).
- Prices are strictly positive - non-positive prices are rejected.
- `volume` is optional (nullable) - not all instruments (e.g. spot forex) reliably report volume; docs/08 §12 only requires it "where required," which Phase 3A does not enforce further (no per-asset volume-requirement rule yet - revisit if a specific asset class needs it).

A candle that fails validation is logged (asset, timeframe, timestamp, reason) and dropped - it does not fail the entire ingestion batch (one bad candle should not block the rest of a batch).

---

# 6. Duplicate Detection

`price_candles` gets a **unique constraint on `(asset_id, timeframe, timestamp)`** - docs/03 §5 only specifies an index on this triple, not uniqueness, but docs/34 explicitly requires "Duplicate Detection" and a candle for a given asset/timeframe/timestamp is logically singular. This will be recorded as **ADR-024** once implemented, following the ADR-022 precedent for inferred schema decisions.

Ingestion is idempotent: inserting a candle that already exists (same `asset_id`/`timeframe`/`timestamp`) is an upsert (`ON CONFLICT (asset_id, timeframe, timestamp) DO UPDATE`), not an error - a re-fetched or corrected candle (e.g. a provider revising a still-forming candle) simply overwrites the stored one. This also makes re-running a collection job safe to retry without special-casing "already have this data."

---

# 7. Retry Policy

Transient provider failures (timeouts, 5xx, rate-limit responses) are retried with exponential backoff, capped at a configurable maximum attempt count. This lives as a wrapper `MarketDataService` applies around any provider call, not inside each provider - so every provider gets the same retry behavior for free and a provider implementation only needs to raise a distinguishable exception type for "transient, worth retrying" vs. "permanent, don't retry" (e.g. invalid API key, unsupported symbol).

`MockMarketDataProvider` never fails, so this path isn't exercised until Phase 3B, but the wrapper is written provider-agnostically now so Phase 3B doesn't require changing `MarketDataService`.

Configuration (per docs/06 §14 "Configuration Over Hardcoding," ADR-017): retry count and backoff base live in `Settings`, not hardcoded.

---

# 8. Failover Strategy

Per docs/34's failover chain (Primary → Secondary → Cached Data → Maintenance Mode):

`MarketDataService` is constructed with an **ordered list** of providers, not a single provider. On a request, it tries each provider in order; if every provider fails (after each one's own retry budget is exhausted, §7), it falls back to the most recent cached/stored data already in `price_candles` for that asset/timeframe (serving slightly-stale data rather than none). If there is no cached data either, the request fails with a typed error the caller (the scheduler, §9) can log and alert on - there is no separate "maintenance mode" flag in Phase 3A; that's effectively the state of "every provider and the cache both failed," which is already observable via logs/health checks (§9) without inventing a new persisted status.

Phase 3A has only one provider (`MockMarketDataProvider`) in the list, so failover to a second provider isn't exercised until Phase 3B adds Twelve Data (and, per BACKLOG.md, a real fallback provider is still an open item beyond that).

---

# 9. Scheduler Architecture

A `MarketDataScheduler` interface (`app/services/market_data/scheduler.py`) defines how periodic collection is triggered, decoupled from *what* triggers it:

- `schedule(asset: Asset, timeframe: Timeframe) -> None` - register a periodic collection job for an asset/timeframe pair.
- Concrete implementation for Phase 3A: a Celery Beat-backed scheduler (Celery/Redis already exist in the stack since Phase 1, per ADR and docs/06 §2), with one periodic task per distinct timeframe (not per asset - a single task for "all M1 assets," etc., to avoid registering hundreds of near-identical Celery Beat entries) that iterates active assets (`Asset.is_active`) for that timeframe and calls `MarketDataService.collect(asset, timeframe)`.
- The interval for each timeframe's task matches that timeframe (e.g. the H1 task runs every hour) **except that it is never shorter than `settings.market_data_min_collection_interval_seconds` (default 300s, Phase 9H, ADR-140)** - `build_beat_schedule_seconds()` applies `max(timeframe_duration, floor)`. This floor exists because the naive "match the timeframe exactly" rule let M1 collect every 60 seconds (1,440 runs/day/asset), which silently exhausted Twelve Data's 800/day free-tier cap roughly four hours into every day and went undetected for a full production outage cycle - collecting *more* often than the provider's real budget allows is exactly as broken as under-polling, not merely wasteful. The floor is lossless (each fetch backfills via `outputsize=5000` + upsert, §6/§7) at the cost of added latency, not lost data.
- This addresses the gap noted in BACKLOG.md: docs/02 §11's Celery task list didn't mention price collection - it's now an explicit Celery Beat responsibility, matching the pattern already used for news/economic collection.

`MockMarketDataProvider` makes this fully testable without needing real Celery Beat timing in unit tests - the scheduler interface can be invoked directly (`scheduler.schedule(...)` calling `service.collect(...)` synchronously in a test) without waiting on real intervals.

---

# 10. Provider Lifecycle

- **Selection**: `settings.market_data_providers: list[str]` (e.g. `["mock"]` today, `["twelve_data", "mock"]` once Phase 3B adds a real provider with Mock as an explicit last-resort fallback if desired) - configured via environment variable, not hardcoded (ADR-017).
- **Construction**: a small factory (`get_market_data_providers() -> list[MarketDataProvider]` in `app/dependencies/market_data.py`) maps each configured name to a concrete provider instance. This is the only place that knows concrete provider classes exist - everything else depends on the `MarketDataProvider` interface (§2).
- **Registration of new providers**: adding a provider means (a) implementing `MarketDataProvider` in its own module under `app/services/market_data/providers/`, (b) adding its name to the factory's mapping, (c) adding it to `settings.market_data_providers`. No changes to `MarketDataService`, repositories, or the scheduler are needed - this is the concrete mechanism that satisfies "additional providers can be added without changing the service layer."
- **Startup/health**: each provider's `health_check()` (§2) can optionally be surfaced through `/health/ready` in a later phase (not built in 3A - no route changes were part of this scope; recorded in BACKLOG.md as a future integration point).

---

# 11. Data Model (Phase 3A)

Per docs/03 §5, with the gaps already tracked in BACKLOG.md §1 resolved using the established `CreatedAtMixin`/`TimestampMixin` pattern from Phase 1.2B/2A:

`Asset` (`TimestampMixin` - mutable reference data; `is_active` can be toggled): `id`, `symbol` (unique), `name`, `market_type` (new enum: `FOREX`, `METAL`, `CRYPTO`, `INDEX` - covering docs/01's "Forex, Gold, Crypto, Indices"), `exchange` (nullable - not all instruments have one), `base_currency`, `quote_currency` (both nullable - indices like `US30` don't have currency pairs), `is_active`.

`Candle` → `price_candles` table (`CreatedAtMixin` - immutable once written, updates only happen via the upsert described in §6, which is a data-correction path, not a mutable-entity `updated_at` concern): `id`, `asset_id` (FK → assets, `CASCADE`), `timeframe`, `timestamp`, `open`, `high`, `low`, `close`, `volume` (nullable), with the unique constraint from §6.

`indicator_results` (unchanged scope from docs/03 §6, populated by the indicator-calculation engine - raw values only, no synthesis per the Phase 3/4 boundary decision): `id`, `asset_id`, `timeframe`, `indicator`, `value`, `metadata`, `calculated_at`.

---

# 12. Out of Scope for Phase 3A

- Any real external provider (Twelve Data lands in Phase 3B).
- A persisted `provider_symbol_map` table (§3).
- Surfacing provider health through `/health/ready` (§10).
- Indicator synthesis, trend detection, technical scoring (Phase 4, per docs/08 §7-11).
- SMC engine, market regime, confidence engine (Phase 4).
- WebSocket price streaming to frontend clients (docs/02 §13 - separate concern from backend ingestion, deferred per BACKLOG.md's existing WebSocket-endpoints entry).

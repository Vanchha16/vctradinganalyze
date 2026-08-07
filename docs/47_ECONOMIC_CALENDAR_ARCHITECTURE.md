# Economic Calendar Architecture

# 1. Scope

Phase 5B's `EconomicCalendarEngine` (`app/services/economic_calendar_engine.py`) collects, normalizes, classifies, and exposes macroeconomic calendar events - it never generates a BUY/SELL/WAIT recommendation (docs/14 §1, ADR-031/ADR-043's no-recommendation precedent extended here). docs/14 §11's "Risk Rules" (reduce confidence, recommend WAIT near critical events) belong to a future Risk Engine/AI Orchestrator, not this engine.

Not wired into `AnalysisConfidenceEngine` in this phase - ADR-047 reserved that integration for a future ADR once Economic Calendar (this engine) exists. Do not add it to `confidence_aggregator.combine()`'s component list as part of Phase 5B.

See docs/14_ECONOMIC_CALENDAR_ENGINE.md for the product-level vision this document implements (and narrows into concrete, buildable decisions).

---

# 2. Persistence Model (ADR-057)

A single `economic_events` table, `UUIDMixin` + `TimestampMixin` - mutable, unlike News's append-only `news_articles` (ADR-053). `actual`/`surprise`/`status` update in place as an event moves through its lifecycle; `updated_at` tracks that. No separate `economic_sources` table (ADR-057) - a plain `source: str` column is sufficient since this domain has no source-credibility-tier axis, unlike News.

Natural key: unique composite index on `(country, currency, event_name, release_time)` - the identity of "the same event," used for upsert (ADR-058), mirroring `SMCEventRepository.get_by_natural_key`'s pattern.

---

# 3. Data Flow

Unlike News (insert-skip-on-duplicate), and unlike every stateless Phase 4 engine, Economic Calendar's write path is an **upsert**:

```
Ingestion path (Celery Beat scheduled, write path):
EconomicCalendarIngestionPipeline.run()
  -> EconomicCalendarProvider.fetch_events(now - lookback_days, now + lookahead_days)  [ADR-056]
  -> for each RawEconomicEvent:
       category_classifier.classify(event_name)                    [ADR-059]
       importance_scorer.score(category, event_name)                [ADR-059]
       surprise_calculator.calculate(actual, forecast)               [only if actual present]
       EconomicEventRepository.get_by_natural_key(...)
       -> if found: update changed fields in place, set status=REVISED if actual changed on
          a row that already had a non-null actual                  [ADR-058]
       -> if not found: create with status=SCHEDULED or RELEASED (actual present at first fetch)

Read path (on-demand, API-triggered):
EconomicCalendarEngine.list_events(filters) / get_upcoming(...) / get_by_id(...)
  -> EconomicEventRepository.find_paginated(...) / find_upcoming(...)
  -> for each event: risk_window.is_in_risk_window(now, release_time, importance)  [ADR-061, computed, not stored]
  -> for each event with a surprise: bias_analyzer.analyze(category, surprise_direction)  [ADR-060]
  -> EconomicCalendarResult
```

The ingestion path never blocks on anything AI-related - there is no AI/GPT anywhere in this engine (unlike News's isolated `ai_summary_generator`). Every field is deterministic.

---

# 4. Module List

```
app/models/economic_event.py                        # EconomicEvent(Base, UUIDMixin, TimestampMixin)
app/models/enums/economic_event_category.py          # 7 values (docs/14 §3)
app/models/enums/economic_event_importance.py        # 4 values, distinct from NewsImportance (ADR-059)
app/models/enums/economic_event_status.py            # SCHEDULED / RELEASED / REVISED / CANCELLED

app/repositories/economic_event_repository.py

app/services/economic_calendar/providers/base.py     # EconomicCalendarProvider Protocol (ADR-056)
app/services/economic_calendar/providers/mock.py     # MockEconomicCalendarProvider
app/services/economic_calendar/providers/exceptions.py

app/services/economic_calendar/types.py               # RawEconomicEvent, EconomicEventEvidence, MarketBias, SurpriseDirection
app/services/economic_calendar/category_classifier.py # ADR-059
app/services/economic_calendar/importance_scorer.py   # ADR-059
app/services/economic_calendar/surprise_calculator.py
app/services/economic_calendar/bias_analyzer.py        # ADR-060
app/services/economic_calendar/risk_window.py          # ADR-061 (pure function, no persistence)

app/services/economic_calendar_engine.py              # read-path orchestrator
app/services/economic_calendar_ingestion_pipeline.py  # write-path orchestrator (upsert, ADR-058)

app/dependencies/economic_calendar.py
app/schemas/economic_calendar.py
app/api/v1/routes/economic_calendar.py
app/workers/economic_calendar_tasks.py
```

---

# 5. Category & Importance Rule Tables (ADR-059)

**Category** (`category_classifier.py`) - keyword match against `event_name`, first match wins, evaluated in this order (specific "Other"-bucket PMI variants checked *before* the generic "PMI" keyword, since docs/14 §3 lists both "PMI" under Growth and "Manufacturing PMI"/"Services PMI" under Other):

| Order | Category | Keywords |
|---|---|---|
| 1 | `CENTRAL_BANK` | fomc, interest rate decision, ecb, boe, boj, rba, rbnz, boc, snb |
| 2 | `INFLATION` | cpi, core cpi, ppi, core ppi, consumer price, producer price |
| 3 | `EMPLOYMENT` | non-farm payroll, nfp, unemployment rate, average hourly earnings, jobless claims |
| 4 | `HOUSING` | building permits, housing starts, existing home sales |
| 5 | `CONSUMER` | consumer confidence, consumer sentiment |
| 6 | `OTHER` (specific) | trade balance, current account, manufacturing pmi, services pmi |
| 7 | `GROWTH` | gdp, retail sales, pmi, industrial production |
| default | `OTHER` | no keyword matched |

**Importance** (`importance_scorer.py`) - first match wins, directly encodes docs/14 §4's worked examples:

| Rule | Importance |
|---|---|
| `event_name` matches FOMC / Interest Rate Decision / NFP / Non-Farm Payroll / CPI / Core CPI / GDP | `CRITICAL` |
| `category == CENTRAL_BANK` | `HIGH` |
| `category == GROWTH` | `HIGH` |
| `category == INFLATION` (catches PPI/Core PPI, not overridden above) | `HIGH` |
| `category == EMPLOYMENT` (catches Unemployment Rate/Avg Hourly Earnings/Jobless Claims) | `HIGH` |
| `category == CONSUMER` | `HIGH` |
| `category == HOUSING` | `MEDIUM` |
| `category == OTHER` and `event_name` in {Trade Balance, Current Account, Manufacturing PMI, Services PMI} | `MEDIUM` |
| else | `LOW` |

---

# 6. Market Bias Rule Table (ADR-060)

`bias_analyzer.analyze(category, surprise_direction) -> dict[str, MarketBias]`, generalizing docs/14 §7's CPI example across all 7 categories. `surprise_direction` is `HIGHER_THAN_FORECAST` / `LOWER_THAN_FORECAST` / `IN_LINE` (from `surprise_calculator`). `MarketBias` is one of `POTENTIALLY_BULLISH` / `POTENTIALLY_BEARISH` / `NEUTRAL` - never a bare `BULLISH`/`BEARISH`, preserving docs/14 §7's "potential impact, not guaranteed direction" language.

| Category | Direction | `currency` | `gold` | `equities` |
|---|---|---|---|---|
| `INFLATION` | Higher than forecast | Potentially Bullish | Potentially Bearish | Potentially Bearish |
| `INFLATION` | Lower than forecast | Potentially Bearish | Potentially Bullish | Potentially Bullish |
| `CENTRAL_BANK` | Higher/hawkish than forecast | Potentially Bullish | Potentially Bearish | Potentially Bearish |
| `CENTRAL_BANK` | Lower/dovish than forecast | Potentially Bearish | Potentially Bullish | Potentially Bullish |
| `EMPLOYMENT` | Stronger than forecast | Potentially Bullish | Potentially Bearish | Potentially Bullish |
| `EMPLOYMENT` | Weaker than forecast | Potentially Bearish | Potentially Bullish | Potentially Bearish |
| `GROWTH` | Stronger than forecast | Potentially Bullish | Potentially Bearish | Potentially Bullish |
| `GROWTH` | Weaker than forecast | Potentially Bearish | Potentially Bullish | Potentially Bearish |
| `CONSUMER` | Stronger than forecast | Potentially Bullish | Potentially Bearish | Potentially Bullish |
| `CONSUMER` | Weaker than forecast | Potentially Bearish | Potentially Bullish | Potentially Bearish |
| `HOUSING` | Stronger than forecast | Potentially Bullish | Neutral | Potentially Bullish |
| `HOUSING` | Weaker than forecast | Potentially Bearish | Neutral | Potentially Bearish |
| `OTHER` | any | Neutral | Neutral | Neutral |
| any | `IN_LINE` (no surprise) | Neutral | Neutral | Neutral |

Only the `INFLATION` row is sourced directly from docs/14 §7's worked example; every other row is this project's own hand-tuned extrapolation (ADR-060's explicit caveat) - a starting point, not an authoritative macro-finance claim, subject to the same "not empirically calibrated" caveat as every prior scoring table (ADR-028/030/035/036/037/042/046/055/059).

---

# 7. Risk Window (ADR-061)

```python
def is_in_risk_window(now: datetime, release_time: datetime, importance: EconomicEventImportance) -> bool:
    delta = release_time - now
    if importance is EconomicEventImportance.CRITICAL:
        return timedelta(minutes=-30) <= delta <= timedelta(minutes=30)
    if importance is EconomicEventImportance.HIGH:
        return timedelta(minutes=0) <= delta <= timedelta(minutes=60)
    return False
```

Pure function, no persistence - computed fresh on every read (API response), never a stored column. See ADR-061 for why a stored boolean would be a correctness bug waiting to happen.

---

# 8. Provider Abstraction (ADR-056)

```python
class EconomicCalendarProvider(Protocol):
    name: str
    def fetch_events(self, start: datetime, end: datetime) -> list[RawEconomicEvent]: ...
    def health_check(self) -> bool: ...
    def capabilities(self) -> EconomicCalendarProviderCapabilities: ...
```

`MockEconomicCalendarProvider` (`app/services/economic_calendar/providers/mock.py`) is the **only** implementation shipped in Phase 5B - a sha256-seeded deterministic generator (mirroring `MockNewsProvider`/`MockMarketDataProvider`) spanning both past (with `actual` populated) and future (`actual=None`, `SCHEDULED`) events across the 7 categories. No real vendor in Phase 5B - TradingEconomics is the target for a follow-up sub-phase (ADR-056), pending provisioning.

Exception hierarchy (`app/services/economic_calendar/providers/exceptions.py`) mirrors News's exactly: `EconomicCalendarProviderError` base, `TransientEconomicCalendarProviderError` / `PermanentEconomicCalendarProviderError` / `EconomicCalendarProviderConfigurationError` / `AllEconomicCalendarProvidersFailedError`.

**Update (Phase 9G, ADR-139):** `AllEconomicCalendarProvidersFailedError` above existed in this hierarchy since Phase 5B but was never raised anywhere until this phase - `EconomicCalendarIngestionPipeline.run()` now raises it if every configured provider fails, and returns `CalendarIngestionResult` (`created`, `updated`, `provider_outcomes: list[ProviderOutcome]`) instead of a bare `(created, updated)` tuple otherwise. This closes the mirror-image problem to News's defect: the calendar *does* produce data even when misconfigured (mock is never-failing by design), so the risk here was `GET /calendar` silently serving synthetic events with nothing indicating the configured provider is a mock - now surfaced via `Pipeline.provider_names`/`.uses_mock` in `GET /admin/system` (docs/58 §3.2). Finnhub activation (`providers/finnhub.py`/`finnhub_http.py`, Phase 7E-B) remains configuration-only, unchanged by this phase - see ADR-139 for exactly what the operator needs to set.

---

# 9. Not Timeframe-Scoped

Like News (docs/46 §10), Economic Calendar has **no `timeframe` parameter** anywhere - it is date/window scoped (`from`/`to`, or the `upcoming` convenience endpoint), not candle-timeframe scoped. Every Phase 4 engine's `analyze(asset, timeframe)` pattern does not apply here; `EconomicCalendarEngine`'s methods take date-range filters instead.

---

# 10. Testing Strategy

| File | Covers |
|---|---|
| `test_economic_category_classifier.py` | Each of the 7 categories, the PMI/Manufacturing-PMI/Services-PMI ordering edge case, default fallback |
| `test_economic_importance_scorer.py` | Every rule-table row, docs/14 §4's worked examples as literal test cases |
| `test_economic_surprise_calculator.py` | Higher/lower/in-line/missing-actual cases |
| `test_economic_bias_analyzer.py` | Every `(category, direction)` row, `IN_LINE` always neutral |
| `test_economic_risk_window.py` | Critical ±30min boundary, High -60min boundary (one-sided), Medium/Low always false, exact-boundary cases |
| `test_mock_economic_calendar_provider.py` | Deterministic seeded generation, spans past+future, `health_check()` always true |
| `test_economic_calendar_ingestion_pipeline.py` | Create-on-first-fetch, upsert-updates-changed-fields-only, `REVISED` status transition, provider-failure handling |
| `test_economic_calendar_engine.py` | Read-path filtering/pagination against persisted fixtures, risk_window/bias computed not read from DB |
| `test_economic_calendar_routes.py` | `GET /calendar` filtering/sorting/pagination, `GET /calendar/{id}` 404, `GET /calendar/upcoming`, no-auth-required |

Verified by inspection (every rule/scenario has a dedicated test), consistent with Phase 5A's practice - coverage tooling is still not installed (BACKLOG.md §4).

---

# 11. Out of Scope for Phase 5B

Real vendor integration (TradingEconomics, ADR-056's follow-up); Confidence Engine integration/weight rebalancing (ADR-047's boundary - do not touch `analysis_confidence_engine.py`/`confidence_aggregator.py`); revision-history audit trail (single mutable row only, ADR-057); automated stale-event cleanup/archival; `/calendar/today`, `/calendar/week`, `/calendar/high-impact`, `/calendar/currency/{currency}` as dedicated routes (`GET /calendar`'s filters absorb them); any Risk Engine logic (docs/14 §11); any AI/GPT usage anywhere in this engine.

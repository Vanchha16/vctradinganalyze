# Smart Money Concepts (SMC) Architecture

Version: 1.0

Status: Phase 4B - Smart Money Concepts Engine. Deterministic structural evidence only (ADR-031, ADR-036) - no BUY/SELL signals, no AI, no probabilistic reasoning. News/Economic analysis (Phase 5) and AI Orchestrator integration (Phase 6) remain out of scope.

---

# 1. Scope

This document defines the architecture of `SMCEngine` and its analyzers - how docs/09's requirements (market structure, BOS, CHOCH, order blocks, fair value gaps, liquidity, premium/discount, confluence) are actually implemented, including decisions inferred beyond the literal text of docs/09 (recorded as ADR-032 through ADR-037, following the ADR-027→031 precedent from Technical Analysis).

Source of truth for the pieces this document describes:

- `app/services/market_structure/` (swing-point detection, shared with Technical Analysis)
- `app/services/smc/` (analyzers, types, scoring)
- `app/services/smc_engine.py` (the top-level orchestrator)
- `app/models/smc_event.py`, `app/models/smc_processing_state.py`
- `app/repositories/smc_event_repository.py`, `app/repositories/smc_processing_state_repository.py`
- `app/schemas/smc.py`, `app/api/v1/routes/smc.py`

---

# 2. Persistence (ADR-032) - Contrast with Technical Analysis

Unlike the stateless `TechnicalAnalysisEngine` (ADR-027), `SMCEngine` persists detected structures to `smc_events` (docs/03 §7). Two reasons drove this reversal:

1. docs/03 §7 already specifies the `smc_events` table - Technical Analysis had no equivalent documented table.
2. SMC concepts have genuine **lifecycle state** (an order block is fresh, then touched, then mitigated or invalidated) that a point-in-time indicator snapshot does not have. Recomputing from scratch on every request would lose that history.

Each `analyze()` call bounds its work to the most recent `_DEFAULT_LOOKBACK` (500) candles rather than the asset's full history - this is what keeps repeated calls fast as history grows, without requiring a full delta-only incremental scan (see §14).

---

# 3. Swing-Point Reuse (avoiding duplicated logic)

`app/services/market_structure/swing_points.py` was extracted from Technical Analysis's `support_resistance_analyzer.py` (which previously had a private `_find_swing_points`). Both `SupportResistanceAnalyzer` and SMC's `MarketStructureAnalyzer`/`BOSAnalyzer`/`LiquidityAnalyzer` now call the same `find_swing_points()` - the one deliberate touch to otherwise-stable Phase 4A code, justified by docs/09 §3 explicitly listing swing highs/lows as required SMC input, and by the project's "do not duplicate Technical Analysis logic" constraint.

---

# 4. Analyzer Dependency Graph

```
                    find_swing_points (shared)
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
   MarketStructureAnalyzer  │      LiquidityAnalyzer
              │             │              │
              ▼             │              ▼
        BOSAnalyzer ────────┘        (zones, sweeps)
              │
              ▼
        CHOCHAnalyzer
              │
              ▼
     OrderBlockAnalyzer
         ┌────┴────┐
         ▼         ▼
MitigationAnalyzer  BreakerBlockAnalyzer   (each consumes OrderBlockAnalyzer's
                                             evidence, not raw candles again)

FairValueGapAnalyzer        PremiumDiscountAnalyzer     (independent - raw candles only)

ConfluenceAnalyzer  ← consumes MarketStructure + BOS + OrderBlocks + PremiumDiscount + Sweeps
SMCConflictAnalyzer ← consumes MarketStructure across timeframes (multi-timeframe only)
SMCScoringEngine    ← consumes everything above + Confluence
```

This is a strict DAG - no analyzer both produces input for, and consumes output from, another analyzer. `MitigationAnalyzer` and `BreakerBlockAnalyzer` both read `OrderBlockAnalyzer`'s evidence and the raw candle window (to check later price interaction against already-detected zones); neither re-runs swing/BOS detection.

---

# 5. Data Flow

```
Asset + Timeframe
       │
       ▼
PriceCandleRepository.list_recent(limit=500)
       │
       ▼
MarketStructureAnalyzer, BOSAnalyzer, CHOCHAnalyzer, OrderBlockAnalyzer (+ Mitigation + Breaker),
FairValueGapAnalyzer, LiquidityAnalyzer, PremiumDiscountAnalyzer
       │
       ▼
ConfluenceAnalyzer  →  SMCScoringEngine  →  SMCScoreBreakdown
       │
       ▼
_archive_stale_order_blocks / _archive_stale_fair_value_gaps (ADR-037)
       │
       ▼
Persist to smc_events (de-duplicated by natural key) + SMCProcessingState checkpoint
       │
       ▼
SMCAnalysisResult (docs/09 §17 corrected shape)
```

`analyze_multi_timeframe()` runs `MarketStructureAnalyzer` once per timeframe (W1, D1, H4, H1, M15) and combines the five states via `multi_timeframe_analyzer.combine()` (ADR-036), plus `SMCConflictAnalyzer` comparing the highest and lowest available timeframes (docs/09 §16).

---

# 6. Evidence Model (corrects docs/09 §17)

docs/09 §17's flat example (`"bos": true, "choch": false, "smc_score": 87`) contradicts §6/§7's own record-based description of BOS/CHOCH. The corrected, list-based shape (implemented in `app/services/smc/types.py` and `app/schemas/smc.py`):

```json
{
    "market_structure": {"state": "bullish", "classifications": [...]},
    "bos": [...],
    "choch": [...],
    "order_blocks": [...],
    "fair_value_gaps": [...],
    "liquidity_zones": [...],
    "liquidity_sweeps": [...],
    "premium_discount": {...},
    "confluence": {"factors": [...], "confluence_score": 0-100},
    "smc_score": 0-100,
    "score_breakdown": {...},
    "warnings": [...]
}
```

`smc_score` and `technical_score` are never combined by either engine (ADR-036) - `smc_score` measures institutional-structure evidence strength (freshness, alignment, confluence), `technical_score` measures indicator agreement. Confluence (docs/09 §14) is one component feeding `smc_score`, not a second competing score.

---

# 7. Lifecycle States (ADR-037)

Persisted zone-type events (`ORDER_BLOCK_*`, `FAIR_VALUE_GAP_*`, `LIQUIDITY_*`) carry a `status` column with four states:

```
ACTIVE ──▶ MITIGATED ──▶ ARCHIVED
   └────▶ INVALIDATED ──▶ ARCHIVED
```

- **ACTIVE**: untouched since detection.
- **MITIGATED**: price closed within the zone (order blocks/FVGs) or the level was swept (liquidity).
- **INVALIDATED**: price closed cleanly through the zone's far side (order blocks only - see §10).
- **ARCHIVED**: resolved (MITIGATED/INVALIDATED) for more than `_ARCHIVE_AFTER` (30 days) - a housekeeping transition, not a deletion. Rows are never deleted (per explicit instruction); archiving only changes `status`.

This is a deliberate departure from every other table in this project (`price_candles`, `indicator_results`, `audit_logs` are all append-only/immutable once written). `smc_events` rows for zone-type concepts are **mutable** - the same row's `status`/`context` update in place as later candles interact with it, looked up via a natural key (`asset_id`, `timeframe`, `event_type`, `detected_at`) rather than re-inserted (`SMCEventRepository.get_by_natural_key` / `update_status`).

BOS, CHOCH, and swing-point (`SWING_HH`/`SWING_HL`/`SWING_LH`/`SWING_LL`) events are point-in-time facts with no natural MITIGATED/INVALIDATED transition - they stay ACTIVE until archived by age.

---

# 8. Processing State (recovery/migration support)

`SMCProcessingState` (one row per asset/timeframe) stores `last_processed_timestamp`, `last_processed_at`, and `engine_version` (`SMC_ENGINE_VERSION` in `smc_engine.py`, currently `"1.0.0"`). It is updated on every `analyze()` call. This is bookkeeping, not detected evidence - it exists to support future recovery/migration scenarios (e.g. detecting that a stored `engine_version` predates an algorithm change, and deciding whether a full re-scan is warranted) rather than to drive today's candle-fetch window, which is always the fixed `_DEFAULT_LOOKBACK`.

---

# 9. Analyzer Responsibilities

| Analyzer | Module | Input | Output |
|---|---|---|---|
| MarketStructureAnalyzer | `market_structure_analyzer.py` | Swing highs/lows | HH/HL/LH/LL classifications + overall state |
| BOSAnalyzer | `bos_analyzer.py` | Candles + swing points | `BOSEvidence` list |
| CHOCHAnalyzer | `choch_analyzer.py` | Classification timeline + BOS events | `CHOCHEvidence` list |
| OrderBlockAnalyzer | `order_block_analyzer.py` | Candles + BOS events | `OrderBlockEvidence` list |
| MitigationAnalyzer | `mitigation_analyzer.py` | Candles + OrderBlockAnalyzer's evidence | Updated order blocks (touched/mitigated) |
| BreakerBlockAnalyzer | `breaker_block_analyzer.py` | Candles + OrderBlockAnalyzer's evidence | Updated order blocks (broken/breaker) |
| FairValueGapAnalyzer | `fair_value_gap_analyzer.py` | Candles | `FairValueGapEvidence` list (fill-checked inline) |
| LiquidityAnalyzer | `liquidity_analyzer.py` | Swing highs/lows + candles | Liquidity zones + sweeps |
| PremiumDiscountAnalyzer | `premium_discount_analyzer.py` | Candles + current price | Live, never persisted (§11) |
| ConfluenceAnalyzer | `confluence_analyzer.py` | All of the above | `ConfluenceEvidence` |
| SMCConflictAnalyzer | `conflict_analyzer.py` | Two `MarketStructureState`s | `SMCConflictReport` (docs/09 §16) |
| SMCScoringEngine | `scoring_engine.py` | All evidence + confluence | `SMCScoreBreakdown` |
| SMCMultiTimeframeAnalyzer | `multi_timeframe_analyzer.py` | Per-timeframe structure states | `SMCVerdict` (ADR-036) |

Every analyzer is a pure function over plain dataclasses (no database access, no I/O, no randomness) - persistence and orchestration live only in `SMCEngine`.

Explicitly **not implemented** (undocumented in docs/09, per "never invent architecture"): Inverse Fair Value Gaps (IFVG), Internal/External BOS distinction, a dedicated Displacement analyzer, Market Imbalance. Displacement's role (identifying the impulsive move behind a BOS) is folded into `OrderBlockAnalyzer`'s candle-pattern definition (§10) rather than exposed as its own concept.

---

# 10. Order Block Algorithm (ADR-034)

docs/09 §8 doesn't define the precise candle pattern. Implemented definition: the **last opposite-colored candle before the displacement move that produces a BOS** - for a bullish BOS, the last bearish (`close < open`) candle in the `_LOOKBACK_LIMIT` (10) candles preceding the break; for a bearish BOS, the last bullish candle. Zone = that candle's high/low.

- **Strength score**: displacement size (`|break_price - zone_high|`) relative to the zone's own range - a simple, deterministic proxy that avoids coupling this analyzer to Technical Analysis's ATR implementation.
- **Freshness score**: `max(0, 1 - candles_since_creation / 50)` - decays linearly, floored at 0.
- **Volume confirmation**: the order-block candle's volume exceeds the mean of the preceding 20 candles' volume.
- **Mitigation** (`mitigation_analyzer.py`): `touched` = any later candle's wick overlaps the zone; `mitigated` = a later candle *closes* within the zone.
- **Breaker** (`breaker_block_analyzer.py`): `broken`/`INVALIDATED` = a later candle closes beyond the zone's far side. If price later retests the same zone and a subsequent candle continues in the new direction, `is_breaker`/`breaker_confirmed` are set - tracked as flags on the same row, not a separate event type.

---

# 11. Fair Value Gap Algorithm

Classic 3-candle gap: bullish when `candle[i-2].high < candle[i].low`; bearish when `candle[i-2].low > candle[i].high`. `priority` (`high`/`medium`/`low`) is the gap's size relative to the middle (displacement) candle's own range. Fill-state is checked against the same candle window immediately (bullish/bearish direction determines which side must be re-entered), so this analyzer - unlike Order Blocks - needs no separate consumer analyzer for lifecycle.

---

# 12. Liquidity Algorithm (ADR-035)

Two or more swing highs (or lows) within a **magnitude-aware tolerance** (5 basis points of price, `_TOLERANCE_RATIO = 0.0005`) form an equal-highs/equal-lows liquidity zone - proportional to price rather than a fixed absolute value, so it generalizes across forex pairs, indices, and gold/crypto price scales. A **sweep** is a wick beyond the level that *closes back inside* it - the mirror image of a BOS, which closes beyond.

---

# 13. Premium/Discount Algorithm

Always computed live from the **current dealing range** (the most recent swing high/low pair, or the full window's high/low if no valid swing pair exists yet) - never persisted, since it has no lifecycle (docs/09 §11). Equilibrium = range midpoint; `distance` is signed and roughly `[-1, 1]` relative to half the range.

---

# 14. Multi-Timeframe Strategy (ADR-036)

Scoped to the five timeframes docs/09 §15 names (Weekly, Daily, H4, H1, M15) - a superset of Technical Analysis's four (ADR-030), so it uses its own weight set: W1=35, D1=30, H4=20, H1=10, M15=5 (sum 100). Same `net/max_possible` alignment-threshold algorithm as Technical Analysis (±0.5). `SMCConflictAnalyzer` compares the highest-priority and lowest-priority available timeframes' `MarketStructureState`; a directional disagreement is classified as a Pullback (docs/09 §16), not a full reversal.

---

# 15. Incremental Scanning - Current Scope and a Documented Simplification

Each `analyze()` call is bounded to `_DEFAULT_LOOKBACK` (500) candles regardless of how much history exists - this alone prevents cost from growing with total history and meets docs/09 §19's performance targets at the scale this phase operates at. Persisted events are de-duplicated against existing rows by natural key, so repeated calls update in place rather than accumulate duplicates.

A **true delta-only scan** - one that skips re-examining candles/zones a prior call already processed, using `SMCProcessingState.last_processed_timestamp` to fetch only genuinely new candles - is a documented future optimization (BACKLOG §13), not implemented in this phase. It requires reconciling newly-fetched candles against already-persisted zone state with more care than the current bounded-window approach, and the bounded window already satisfies the stated performance budget.

---

# 16. API Contract

```
GET /analysis/smc/{symbol}?timeframe=H1
GET /analysis/smc/{symbol}/multi-timeframe
```

Both public (no authentication, matching Technical Analysis's precedent). `{symbol}` reuses the case-insensitive `get_asset_or_404` dependency. Response shapes match docs/04 (updated alongside this document). Filtering query params (`event_type`, `include_mitigated`) were considered but deferred - not implemented this phase (BACKLOG).

---

# 17. Testing Strategy

- Per-analyzer unit tests with synthetic OHLCV fixtures engineered to contain known patterns by construction (`tests/test_swing_points.py`, `tests/test_bos_analyzer.py`, `tests/test_order_block_analyzer.py`, `tests/test_mitigation_analyzer.py`, `tests/test_breaker_block_analyzer.py`, `tests/test_fair_value_gap_analyzer.py`, `tests/test_liquidity_analyzer.py`, `tests/test_premium_discount_analyzer.py`, `tests/test_choch_analyzer.py`, `tests/test_market_structure_analyzer.py`, `tests/test_smc_confluence_analyzer.py`, `tests/test_smc_conflict_analyzer.py`, `tests/test_smc_scoring_engine.py`, `tests/test_smc_multi_timeframe_analyzer.py`).
- Repository/model tests for the mutable-row lifecycle behavior unique to `smc_events` (`tests/test_smc_models.py`).
- Engine-level integration tests for persistence idempotency, insufficient-candle warnings, missing-candle 404s, and the archiving transition (`tests/test_smc_engine.py`).
- API tests mirroring Technical Analysis's pattern - structured evidence shape, case-insensitive symbols, 404s, validation errors, no-auth requirement, persistence-across-calls, multi-timeframe partial data (`tests/test_smc_api.py`).

---

# 18. Out of Scope for Phase 4B

- Any BUY/SELL/WAIT recommendation, entry/stop-loss/take-profit level (ADR-031, ADR-036 - that's the future Signal Engine).
- IFVG, Internal/External BOS, a dedicated Displacement analyzer, Market Imbalance (undocumented in docs/09 - excluded per "never invent architecture").
- True delta-only incremental scanning (§15 - documented future optimization).
- API filtering query params (`event_type`, `include_mitigated`) - considered, deferred.
- News/Economic analysis (Phase 5). AI Orchestrator integration (Phase 6).

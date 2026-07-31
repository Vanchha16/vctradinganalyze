# Technical Analysis Architecture

Version: 1.0

Status: Phase 4A - Technical Analysis Engine. Deterministic evidence generation only (ADR-031) - no BUY/SELL signals, no Smart Money Concepts (Phase 4B), no News/Economic analysis (Phase 5), no AI Orchestrator integration (Phase 6).

---

# 1. Scope

This document defines the architecture of `TechnicalAnalysisEngine` and its analyzers - how docs/08's requirements (trend detection, momentum, volatility, support/resistance, multi-timeframe analysis, technical scoring, conflict detection) are actually implemented, including several decisions inferred beyond the literal text of docs/08 (recorded as ADR-027 through ADR-031, following the ADR-022→026 precedent).

Source of truth for the pieces this document describes:

- `app/services/technical_analysis/` (analyzers, types, scoring)
- `app/services/technical_analysis_engine.py` (the top-level orchestrator)
- `app/schemas/technical_analysis.py`, `app/api/v1/routes/technical_analysis.py`

---

# 2. Statelessness (ADR-027)

`TechnicalAnalysisEngine` persists nothing. Every call to `analyze()`/`analyze_multi_timeframe()` fetches recent candles via the existing `PriceCandleRepository`, computes every registered indicator **fresh** via `app/indicators/registry` (not by reading persisted `indicator_results` rows, which may be up to one Celery Beat cycle stale), and returns a plain in-memory result. No new database table exists for this phase.

---

# 3. Data Flow

```
Asset + Timeframe
       │
       ▼
PriceCandleRepository.list_recent(limit=500)
       │
       ▼
compute_indicator_snapshot()  →  every registered indicator (docs/39), or a warning if unavailable
       │
       ▼
┌──────────────┬─────────────┬────────────────┬───────────────┬─────────────┬────────────────────────┐
│ MovingAverage │  Momentum   │  Oscillator    │  Volatility   │   Volume    │  SupportResistance     │
│  Analyzer     │  Analyzer   │  Analyzer      │   Analyzer    │  Analyzer   │  Analyzer (+ D1 fetch) │
└──────┬───────┴──────┬──────┴───────┬────────┴───────┬───────┴──────┬──────┴───────────┬────────────┘
       │              │              │                │              │                  │
       ▼              │              │                │              │                  │
TrendAnalyzer          │              │                │              │                  │
       │              │              │                │              │                  │
       └──────────────┴──────────────┴────────────────┴──────────────┴──────────────────┘
                                          │
                                          ▼
                                 ConflictAnalyzer
                                          │
                                          ▼
                              TechnicalScoringEngine
                                          │
                                          ▼
                          TechnicalAnalysisResult (docs/08 §11 shape)
```

`analyze_multi_timeframe()` runs the candle-fetch → indicator-snapshot → `TrendAnalyzer` portion of this pipeline once per timeframe (D1, H4, H1, M15) and combines the four `TrendEvidence` results via `MultiTimeframeAnalyzer` (ADR-030) - it does not run the full scoring/conflict pipeline per timeframe, keeping the combined response lightweight (docs/08 §13 performance).

---

# 4. Analyzer Responsibilities

| Analyzer | Module | Input | Output |
|---|---|---|---|
| MovingAverageAnalyzer | `moving_average_analyzer.py` | EMA20/50/100/200, SMA200, current price | `MovingAverageEvidence` (alignment facts) |
| TrendAnalyzer | `trend_analyzer.py` | MA evidence + ADX/DI+/DI- | `TrendEvidence` (final trend + strength, docs/08 §7) |
| MomentumAnalyzer | `momentum_analyzer.py` | MACD, Momentum | `MomentumEvidence` |
| OscillatorAnalyzer | `oscillator_analyzer.py` | RSI, Stochastic RSI, CCI | `OscillatorEvidence` (overbought/oversold/healthy) |
| VolatilityAnalyzer | `volatility_analyzer.py` | ATR, Bollinger Bands, StdDev | `VolatilityEvidence` (squeeze/near-band/stable) |
| VolumeAnalyzer | `volume_analyzer.py` | VWAP, OBV, Relative Volume | `VolumeEvidence` |
| SupportResistanceAnalyzer | `support_resistance_analyzer.py` | Recent candles + D1 candles + current price | `SupportResistanceEvidence` (docs/08 §6, ADR-029) |
| MultiTimeframeAnalyzer | `multi_timeframe_analyzer.py` | TrendEvidence per timeframe | Combined verdict (docs/08 §8, ADR-030) |
| TechnicalScoringEngine | `scoring_engine.py` | All of the above + ConflictReport | `ScoreBreakdown` (docs/08 §9, ADR-028) |
| ConflictAnalyzer | `conflict_analyzer.py` | Trend/Momentum/Oscillator/Volume evidence | `ConflictReport` (docs/08 §10) |

Every analyzer is a pure function operating on plain dataclasses - no database access, no I/O, no randomness (ADR-031). Not in the originally-sketched analyzer list: `VolumeAnalyzer` was added because docs/08 §5 treats Volume (VWAP/OBV/Volume MA/Relative Volume) as its own first-class indicator category, distinct from Momentum/Volatility, and §9's scoring example names "VWAP Above Price" as its own factor.

---

# 5. Missing-Indicator Policy

docs/08 §12 requires rejecting analysis on missing *candles* (enforced - `TechnicalAnalysisEngine.analyze` raises `ResourceNotFoundException` if no candles exist for the asset/timeframe). It does not address an individual indicator being unavailable due to insufficient warm-up history (docs/39 §7 - e.g. `sma_200` needs 200 candles). Policy: **proceed with available indicators**, and add a warning string to the result's `warnings` list for each unavailable indicator (`compute_indicator_snapshot` in `indicator_snapshot.py`) - never silently omit the fact that an indicator was skipped.

---

# 6. Support/Resistance Algorithm (ADR-029)

- **Swing highs/lows**: classic 5-candle fractal (`_FRACTAL_WINDOW = 2` candles on each side) - a candle is a swing high/low if its high/low is the extreme within that window.
- **Daily/weekly/monthly highs/lows**: aggregated from **D1 candles specifically**, fetched independently of the requested analysis timeframe (an H1 analysis request still triggers a separate D1 candle fetch for this purpose).
- **Round numbers/psychological levels**: a single magnitude-aware heuristic (ADR-029) - step size = `10^floor(log10(price)) / 20`, giving a ~0.005 step for a ~1.10 forex pair or a ~100 step for a ~2400 gold/index price, generalizing to any asset without a maintained per-symbol table.
- Levels are merged, filtered to those on the correct side of the current price, sorted by proximity, and the nearest of each direction is exposed as `support`/`resistance`; the fuller candidate list (up to 5 each) is exposed as `support_levels`/`resistance_levels` (Phase 4A refinement - richer evidence for future consumers).
- Each level carries a `source` (e.g. `"swing_high"`, `"daily_high"`, `"round_number"`) and a `strength` (`"weak"` for swing points/round numbers, `"moderate"` for daily/weekly/monthly extremes) - a simple, static classification for this phase, not a multi-source-agreement scoring model. Revisit if levels from multiple sources clustering near the same price should be merged into a single, stronger level (not done in Phase 4A, to avoid over-building before it's needed).

---

# 7. Technical Scoring (ADR-028)

100-point breakdown, each component independently reported (Phase 4A refinement):

| Component | Max | Basis |
|---|---|---|
| Trend | 25 | Moving-average alignment score (§9 below) |
| (Trend strength folded into the same "trend" bucket) | 15 | ADX-derived strength weight |
| Momentum | 15 | MACD direction agreement with the overall trend |
| Oscillator | 15 | RSI health (healthy = full credit, overbought/oversold/unavailable = half) |
| Volume | 15 | VWAP-position agreement with the overall trend |
| Volatility | 10 | Bollinger Band state (stable = full, squeeze/near-band/unavailable = half) |
| Support/Resistance | 5 | Whether both a support and a resistance level were found (proximity context) |

Total = sum of components + penalties (see §8), clamped to `[0, 100]`.

---

# 8. Conflict Detection & Penalties

`ConflictAnalyzer` checks the overall trend direction against MACD direction, ADX-derived strength, RSI extremes, and VWAP position - each contradiction is recorded as a `Conflict` with a human-readable description (surfaced in the result's `warnings`, alongside missing-indicator warnings, for explainability). `TechnicalScoringEngine` subtracts a fixed 10 points per detected conflict from the raw weighted score, floored at 0 overall (ADR-028) - conflicts are additive penalties, not a trend-verdict override (unlike docs/08 §10's own example, which conflates the two; here, the trend classification itself is decided purely by `TrendAnalyzer`, and conflicts only affect the *score*).

---

# 9. Trend Detection (§7 of docs/08)

`TrendAnalyzer` classifies direction purely from `MovingAverageAnalyzer`'s alignment facts: all four EMA pairs (20>50, 50>100, 100>200) in ascending order → bullish; all in descending order → bearish; anything else → sideways. Strength is classified purely from ADX: ≥40 → very strong, ≥25 → strong, ≥20 → moderate, otherwise (or if ADX unavailable) → weak - independent of whether the moving averages happen to be cleanly aligned, since a weak ADX with clean MA alignment still isn't a *strong* trend.

---

# 10. Multi-Timeframe Combination (ADR-030)

Scoped exactly to D1/H4/H1/M15 (docs/08 §8's named timeframes - not generalized to every canonical `Timeframe`). Weights: D1=40, H4=30, H1=20, M15=10 (sum 100). Each timeframe's trend contributes ±its weight to a net total; `net/max_possible ≥ 0.5` → bullish alignment, `≤ -0.5` → bearish alignment, otherwise → mixed. A missing timeframe (no candles yet) is skipped, not treated as neutral/zero - `max_possible` only counts timeframes that actually produced a result.

---

# 11. API Contract

```
GET /analysis/technical/{symbol}?timeframe=H1
GET /analysis/technical/{symbol}/multi-timeframe
```

Both public (no authentication - matching the Phase 3C precedent for non-personalized market reference data). `{symbol}` reuses the case-insensitive `get_asset_or_404` dependency from `app/api/v1/routes/market_data.py`. Response shapes match docs/04 (updated alongside this document).

---

# 12. Out of Scope for Phase 4A

- Any BUY/SELL/WAIT recommendation, entry/stop-loss/take-profit level (ADR-031 - that's the future Signal Engine, docs/30 Phase 6).
- Smart Money Concepts (Phase 4B).
- News/Economic analysis (Phase 5).
- AI Orchestrator integration/combination with SMC/News/Economic/Risk evidence (Phase 6).
- Persisted technical-analysis history (ADR-027).
- Merging multiple support/resistance sources clustering near the same price into a single stronger level (noted in §6 as a possible future refinement).

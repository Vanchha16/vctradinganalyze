# Market Regime Architecture

Version: 1.0

Status: Phase 4C - Market Regime Engine. Deterministic classification only (ADR-031, ADR-038) - no BUY/SELL signals, no AI, no probabilistic reasoning, no strategy recommendations (ADR-043). Confidence Engine (Phase 4D) and beyond remain out of scope.

---

# 1. Scope

This document defines the architecture of `MarketRegimeEngine` and its analyzers - how docs/16's requirements (regime classification, trend strength, volatility regime, consolidation/breakout/exhaustion detection) are actually implemented, including decisions inferred beyond the literal text of docs/16 (recorded as ADR-038 through ADR-044, following the ADR-032→037 precedent from SMC).

Source of truth for the pieces this document describes:

- `app/services/market_regime/` (analyzers, types, classifier, confidence engine)
- `app/services/market_regime_engine.py` (the top-level orchestrator)
- `app/schemas/market_regime.py`, `app/api/v1/routes/market_regime.py`

---

# 2. Regime Taxonomy - Resolving the docs/16 §3 vs. Kickoff-Prompt Conflict

docs/16 §3 defines one flat, mutually-exclusive `regime` enum (Trending Bullish/Bearish, Ranging, Accumulation, Distribution, Breakout, Pullback, Reversal, High/Low Volatility, Uncertain) - this is implemented verbatim as `MarketRegimeState`, **never extended** with values not in docs/16 (no bare "Expansion," "Strong Trend," or "Breakout Environment" as top-level regime values).

Concepts from the Phase 4C kickoff that aren't in docs/16 §3 (Expansion/Contraction, Transition) are implemented as **supporting evidence fields** feeding the classification, not additional regime values: `ExpansionEvidence` and `TransitionEvidence` are returned alongside `regime`, never instead of it.

---

# 3. Statelessness (ADR-038)

`MarketRegimeEngine` persists nothing - like Technical Analysis (ADR-027), not SMC (ADR-032). No `market_regime`/`regime_events` table exists in docs/03, and none is added. A regime classification is a fresh synthesis of Technical Analysis's and SMC's already-computed/already-persisted evidence each time - recomputing it is cheap, since the expensive detection work lives upstream.

---

# 4. Data Flow

```
Asset + Timeframe
       │
       ▼
PriceCandleRepository.list_recent(limit=500)
       │
       ├──────────────► TechnicalAnalysisEngine.analyze()  (called once)
       │
       └──────────────► SMCEngine.analyze()                (called once)
                              │
       ┌──────────────────────┴───────────────────────────────────┐
       ▼              ▼             ▼            ▼                ▼
TrendRegime    VolatilityRegime  Range      Expansion      Transition
Analyzer       Analyzer          Analyzer   Analyzer       Analyzer
       │              │             │            │                │
       └──────┬───────┴─────────────┴────────────┴────────────────┘
              ▼
   AccumulationDistribution, Breakout, PullbackReversal Analyzers
              │
              ▼
      RegimeConflictAnalyzer
              │
              ▼
   RegimeClassifier.build_candidates() ──► classify()  (ADR-039, ADR-044)
              │
              ▼
     RegimeConfidenceEngine.score()  (ADR-042)
              │
              ▼
        MarketRegimeResult
```

Both upstream engines are called **exactly once** per `analyze()` execution and their results passed by parameter to every regime analyzer - never re-invoked per analyzer (Phase 4C refinement).

---

# 5. Reuse Map (avoiding duplicated calculations)

| docs/16 §4 Input | Source |
|---|---|
| ATR, ADX, EMA, VWAP, Support, Resistance | Technical Analysis Engine's `TechnicalAnalysisResult` (extended, §7 below) |
| HH/HL/LH/LL, CHOCH, Strong BOS | SMC Engine's `MarketStructureEvidence`/`CHOCHEvidence`/`BOSEvidence` |
| Volume trend (increasing/stable) | Computed directly from candles - point-in-time only in `VolumeEvidence` |
| ATR *series* (for volatility/expansion regime) | `app/indicators/_utils.py::wilder_smoothed_series` (shared low-level utility, not Technical Analysis's `atr()` analyzer) |
| Economic Risk | Unbuilt (Phase 5) - not consumed this phase |

---

# 6. `TechnicalAnalysisResult` Extension (a justified, additive touch)

`TechnicalAnalysisEngine.analyze()` previously computed `MomentumEvidence`/`OscillatorEvidence`/`VolatilityEvidence`/`VolumeEvidence`/`TrendEvidence` internally, used them only to feed `ScoreBreakdown`, and discarded them - `TechnicalAnalysisResult` only exposed `trend`/`strength` (not the underlying `TrendEvidence`, losing ADX DI+/DI-) and a flat `indicators: dict[str, float]` (losing Bollinger upper/lower and every analyzer's state classification, since only `IndicatorOutput.value` survived the conversion).

Market Regime needs this state directly. `TechnicalAnalysisResult` was extended (Phase 4C) with five new, purely additive fields - `trend_evidence`, `momentum`, `oscillator`, `volatility`, `volume` - exposing the full evidence objects. No existing field was renamed or removed; the public HTTP response (`app/schemas/technical_analysis.py`) is unchanged - these fields are consumed in-process by `MarketRegimeEngine`, not (yet) surfaced over the Technical Analysis API.

---

# 7. Volatility & Expansion Algorithm

`VolatilityRegimeAnalyzer` computes a full ATR series (`true_ranges` + `wilder_smoothed_series`, the same shared utilities Technical Analysis's own `atr()` uses internally) rather than duplicating that calculation, then compares the trailing-14 average against the full-window average. Bands are relative (proportional to the ratio), consistent with ADR-029/ADR-035's magnitude-aware precedent:

| Ratio (recent/baseline) | State |
|---|---|
| < 0.5 | Very Low |
| < 0.8 | Low |
| ≤ 1.25 | Normal |
| ≤ 2.0 | High |
| > 2.0 | Extreme |

`ExpansionAnalyzer` reuses the same recent/baseline averages (no third ATR pass) to classify Expansion (ratio > 1.15) / Contraction (ratio < 0.85) / Stable - supporting evidence, not a top-level regime value (§2).

---

# 8. Range Algorithm

Reuses Technical Analysis's `SupportResistanceEvidence` (nearest support/resistance) directly. Ranging = price sits within `[support, resistance]` *and* `TrendEvidence.strength` is `WEAK` or direction is `SIDEWAYS` - no new threshold invented; the existing ADX-derived strength classification is reused as-is.

---

# 9. Trend-Strength / Accumulation-Distribution / Breakout / Pullback-Reversal Algorithms

- **Trend regime**: `TrendRegimeAnalyzer` combines Technical Analysis's `TrendEvidence` (direction/strength/ADX/EMA) with SMC's `MarketStructureEvidence` (HH/HL/LH/LL state) and flags `aligned` when both agree - never re-derives either.
- **Accumulation/Distribution** (ADR-040): an ACTIVE bullish Order Block or a **sell-side** liquidity sweep are accumulation signals; an ACTIVE bearish Order Block or a **buy-side** liquidity sweep are distribution signals (the standard ICT interpretation of a sweep's directionality - smart money buys from stops below a range low, sells into stops above a range high). Combined with range confirmation and a directly-computed volume trend (candles' recent vs. baseline average volume - not exposed point-in-time-only by Technical Analysis's `VolumeEvidence`).
- **Breakout** (docs/16 §8): SMC's `BOSEvidence` *is* the "break of key level" requirement - no separate break-detection. Only a BOS within the last 3 candles is treated as a live breakout candidate. A subsequent candle closing back through `break_price` reclassifies it `false_breakout`.
- **Pullback/Reversal** (ADR-041): Reversal reuses SMC's `CHOCHEvidence` directly. Pullback depth is a **single-timeframe** retracement measurement using the most recently classified SMC swing high/low - explicitly distinct from SMC's own multi-timeframe Pullback concept (ADR-036/docs/09 §16). Fibonacci-style bands: ≤0.382 Healthy, ≤0.618 Deep, beyond that Potential Reversal. docs/16 §2's undocumented "exhaustion" responsibility is folded in as a warning here (deep retracement, no confirming CHOCH yet) - not a dedicated analyzer or regime value.

---

# 10. Regime Classification Algorithm (ADR-039)

Per Phase 4C approval, **every** candidate regime's confidence is computed first (`RegimeClassifier.build_candidates`), independent of any precedence ordering. Candidates below `MIN_CONFIDENCE_TO_QUALIFY` (60.0) are discarded. Only among the *qualifying* survivors is the documented precedence order applied:

1. Reversal
2. Breakout
3. Distribution / Accumulation (tie-broken by confidence)
4. Trending Bullish / Trending Bearish
5. Pullback
6. Ranging
7. High Volatility / Low Volatility
8. Uncertain (fallback when nothing qualifies)

This resolves docs/16 §3's "Uncertain" ambiguity: it is never a positively-detected condition, only the fallback when no candidate clears the confidence bar.

---

# 11. Classification Stability (ADR-044)

The winning qualifying candidate is compared against the next-best *other* qualifying candidate (`runner_up`). If the margin between them is below `MIN_MARGIN` (10.0 points), the classification is still reported (the higher-precedence/higher-confidence winner still stands - no forced downgrade to Uncertain), but:

- `RegimeConfidenceBreakdown.stability_penalty` is reduced proportionally to how thin the margin is.
- A `warnings` entry names both candidates near the boundary.

This is **not** true cross-request hysteresis (docs/16's "anti-oscillation" framed generally) - the engine is stateless (§3), so there is no persisted prior classification to compare against. What's implemented is a same-request, fully deterministic anti-oscillation safeguard: a classification is only reported at full confidence when it clearly beats its nearest rival *within the same evidence window*, reducing (not eliminating) request-to-request flicker on genuinely marginal data. True temporal hysteresis (remembering the last N classifications) is a documented future option if real request patterns show flip-flopping - see ADR-044 and BACKLOG.

---

# 12. Multi-Timeframe Strategy

Reuses SMC's five-timeframe set (W1/D1/H4/H1/M15, ADR-036) rather than Technical Analysis's four - confirmed on Phase 4C approval, since Market Regime consumes evidence from both engines and SMC's set is a strict superset.

Unlike Technical Analysis's/SMC's multi-timeframe methods (which only need a cheap per-timeframe trend/structure summary), a full regime classification needs the complete evidence set per timeframe. `analyze_multi_timeframe()` therefore calls the full `analyze()` per timeframe - a deliberate, heavier deviation from that precedent, noted here so it isn't mistaken for an oversight. This means SMC persistence (idempotent, de-duplicated) is triggered once per timeframe on a multi-timeframe regime request - correct, if worth knowing when reasoning about request cost.

---

# 13. Confidence vs. `technical_score`/`smc_score` (ADR-042)

`RegimeConfidenceBreakdown` (deliberately not named "*Score*" - Phase 4C refinement) measures how *reliable this specific classification* is: trend clarity, volatility clarity, structural confirmation (the winning candidate's own evidence strength), minus stability and conflict penalties. It is never combined with `technical_score` (indicator agreement) or `smc_score` (institutional structure evidence strength) - three engines, three independent measures, left for the future Signal Engine (Phase 6) to combine.

---

# 14. Strategy Compatibility & AI Integration Are Documentation Guidance, Not Engine Output (ADR-043)

docs/16 §16 ("Strategy Compatibility": e.g. "Ranging → Recommended: Mean Reversion") and §17 ("AI Integration" narrative) both describe strategy-selection guidance, not raw structural evidence - confirmed on Phase 4C approval to be **excluded from engine output entirely**. `MarketRegimeResult`/`MarketRegimeResponse` have no `compatible_strategies`, `recommendation`, or narrative field. §16/§17 remain useful *documentation* for whichever future engine (Signal Engine, AI Orchestrator, Phase 6) decides what to do with a given regime - they are not this engine's responsibility.

---

# 15. API Contract

```
GET /analysis/market-regime/{symbol}?timeframe=H1
GET /analysis/market-regime/{symbol}/multi-timeframe
```

Both public (no authentication, matching Technical Analysis's/SMC's precedent). `{symbol}` reuses the case-insensitive `get_asset_or_404` dependency.

---

# 16. Testing Strategy

- Per-analyzer unit tests with synthetic OHLCV fixtures engineered to contain known patterns by construction (`tests/test_trend_regime_analyzer.py`, `tests/test_volatility_regime_analyzer.py`, `tests/test_expansion_analyzer.py`, `tests/test_range_analyzer.py`, `tests/test_transition_analyzer.py`, `tests/test_accumulation_distribution_analyzer.py`, `tests/test_breakout_analyzer.py`, `tests/test_pullback_reversal_analyzer.py`, `tests/test_market_regime_conflict_analyzer.py`).
- `tests/test_regime_classifier.py` - regression tests specifically for the precedence-after-qualifying rule (§10) and the anti-oscillation margin behavior (§11), including a case engineered so the highest-raw-confidence candidate does *not* win, to prove precedence is genuinely applied only among qualifiers.
- `tests/test_confidence_engine.py` - confidence breakdown composition and conflict/stability penalties.
- `tests/test_market_regime_multi_timeframe_analyzer.py` - the weighted combination algorithm.
- `tests/test_market_regime_engine.py` - integration (missing-candle 404, insufficient evidence, and a test asserting each upstream engine is called exactly once per `analyze()`, proving the caching refinement).
- `tests/test_market_regime_api.py` - structured evidence shape, 404s, validation, no-auth, multi-timeframe partial data, and an explicit assertion that no `recommendation`/`compatible_strategies`/`strategy` field is present (ADR-043).

---

# 17. Out of Scope for Phase 4C

- Any BUY/SELL/WAIT recommendation (ADR-031, ADR-043).
- Strategy Compatibility / AI Integration as engine output (§14, ADR-043).
- True cross-request hysteresis / persisted regime history (§11, ADR-044) - a documented future option, not required to meet docs/16.
- Confidence Engine (Phase 4D) and beyond.

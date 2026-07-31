# Confidence Architecture

# 1. Scope

Phase 4D's `AnalysisConfidenceEngine` (`app/services/analysis_confidence_engine.py`) evaluates the quality, completeness, and consistency of evidence already produced by Technical Analysis, SMC, and Market Regime - it never predicts a trade outcome and never produces a BUY/SELL/WAIT recommendation (ADR-031, ADR-043, extended by ADR-047 for this engine).

Named `AnalysisConfidenceEngine`, not bare `ConfidenceEngine`, to avoid confusion with `app/services/market_regime/confidence_engine.py`'s `RegimeConfidenceEngine`, which scores regime-classification reliability only (ADR-048). See docs/15 for the product-level spec this document implements.

---

# 2. Statelessness (ADR-045)

Fully stateless, mirroring Technical Analysis (ADR-027) and Market Regime (ADR-038), not SMC's persisted-mutable-events pattern (ADR-032/033). No new table, no migration. Every call recomputes from Technical Analysis, SMC, and Market Regime fresh.

---

# 3. Data Flow

```
AnalysisConfidenceEngine.analyze(asset, timeframe)
  -> TechnicalAnalysisEngine.analyze(asset, timeframe)   [or None on ResourceNotFoundException]
  -> SMCEngine.analyze(asset, timeframe)                 [or None on ResourceNotFoundException]
  -> MarketRegimeEngine.analyze(asset, timeframe,
       technical_analysis=<above>, smc=<above>)          [or None on ResourceNotFoundException]
  -> technical_confidence_analyzer.analyze(technical)
  -> smc_confidence_analyzer.analyze(smc)
  -> regime_confidence_analyzer.analyze(market_regime)
  -> alignment_analyzer.analyze(directions)
  -> conflict_analyzer.analyze(technical, smc, market_regime, alignment)
  -> data_quality_analyzer.analyze(technical, smc, market_regime)
  -> freshness_analyzer.analyze(technical, smc, market_regime, timeframe, now)
  -> confidence_aggregator.combine(weighted components, conflict_penalty)
  -> summary_builder.build(...)
  -> ConfidenceResult
```

Each of the three upstream engines is called **at most once** per execution (ADR-049) - Technical Analysis and SMC are computed first and passed by parameter into `MarketRegimeEngine.analyze()`, which accepts them as optional pre-computed arguments rather than always recomputing them itself. This avoids the double-computation a naive three-independent-calls design would cause, since `MarketRegimeEngine.analyze()` already calls both internally by default.

---

# 4. `MarketRegimeEngine` Extension (ADR-049)

```python
def analyze(
    self, asset, timeframe, *,
    technical_analysis: TechnicalAnalysisResult | None = None,
    smc: SMCAnalysisResult | None = None,
) -> MarketRegimeResult:
    technical_analysis = technical_analysis or self._technical_analysis_engine.analyze(asset, timeframe)
    smc = smc or self._smc_engine.analyze(asset, timeframe)
    ...
```

Both new parameters default to `None`, preserving the original always-recompute behavior for every existing caller (the `/analysis/market-regime/*` routes, `analyze_multi_timeframe`). Purely additive - no existing field or method signature removed.

---

# 5. Folder Structure

```
app/services/analysis_confidence_engine.py       # top-level orchestrator
app/services/analysis_confidence/
    types.py                          # ConfidenceLevel, NormalizedDirection, ConflictSeverity,
                                       # AlignmentEvidence, ConflictEvidence, DataQualityEvidence,
                                       # FreshnessEvidence, ConfidenceBreakdown, ConfidenceResult,
                                       # ConfidenceMultiTimeframeResult
    direction_normalizer.py           # maps each engine's own directional vocabulary onto NormalizedDirection
    technical_confidence_analyzer.py  # reframes technical_score -> technical_alignment
    smc_confidence_analyzer.py        # reframes smc_score -> smc_alignment
    regime_confidence_analyzer.py     # reframes Market Regime confidence -> regime_confirmation
    alignment_analyzer.py             # cross-engine directional agreement
    conflict_analyzer.py              # cross-engine contradiction detection (4 rules)
    data_quality_analyzer.py          # missing/thin-evidence detection
    freshness_analyzer.py             # staleness detection per timeframe
    summary_builder.py                # deterministic 2-3 sentence summary
    confidence_aggregator.py          # modular weighted-sum combination + level bands
app/schemas/analysis_confidence.py    # ConfidenceResponse, ConfidenceMultiTimeframeResponse
app/dependencies/analysis_confidence.py
app/api/v1/routes/analysis_confidence.py
```

The three "reframing" analyzers (`technical_confidence_analyzer.py`, `smc_confidence_analyzer.py`, `regime_confidence_analyzer.py`) do not recompute any upstream evidence - each translates one already-computed 0-100 score into this engine's weighted-component terms. This satisfies "avoid duplicating logic from upstream engines" directly.

---

# 6. Confidence Bands

| Range | `ConfidenceLevel` |
|---|---|
| 80-100 | VERY_HIGH |
| 65-79 | HIGH |
| 45-64 | MODERATE |
| 25-44 | LOW |
| 0-24 | VERY_LOW |

Starting-point thresholds (`app/services/analysis_confidence/confidence_aggregator.py::_LEVEL_BANDS`), not tuned against real outcomes - the same caveat every prior scoring ADR (028/030/035/036/037/042) carries.

---

# 7. Scoring Algorithm

| Component | Weight | Source |
|---|---|---|
| `technical_alignment` | 25 | `technical.technical_score / 100 * 25` |
| `smc_alignment` | 25 | `smc.smc_score / 100 * 25` |
| `regime_confirmation` | 20 | `market_regime.confidence / 100 * 20` |
| `cross_engine_agreement` | 20 | `agreement_ratio * 20` (docs/45 §8) |
| `data_completeness` | 5 | `5 - (missing_signals * 5/6)`, floored at 0 |
| `freshness` | 5 | 5 if fresh, 2.5 if any engine stale, 0 if no engine available |
| `conflict_penalty` | -15 floor | sum of per-conflict penalties by severity (LOW -3, MEDIUM -6, HIGH -10) |

`overall_confidence` = sum of the six positive components + `conflict_penalty`, floored at 0 and capped at 100 (`ConfidenceBreakdown.total`, mirrors `ScoreBreakdown.total`/`SMCScoreBreakdown.total`/`RegimeConfidenceBreakdown.total`'s existing floor/cap convention).

Market Regime is weighted at 20 rather than equal to Technical Analysis/SMC's 25 because it is itself derived from both (`MarketRegimeEngine.analyze()` calls `TechnicalAnalysisEngine`/`SMCEngine`) - equal weighting would double-count the same underlying evidence twice. Volatility is deliberately not scored independently here - it flows in only via `regime_confirmation` (Market Regime's own `confidence_breakdown.volatility_clarity`), preventing the same double-count risk for that specific factor (ADR-046).

---

# 8. Alignment Algorithm

`app/services/analysis_confidence/direction_normalizer.py` maps every engine's own vocabulary onto `NormalizedDirection` (`BULLISH`/`BEARISH`/`NEUTRAL`):

| `NormalizedDirection` | Technical Analysis `trend` | SMC `market_structure.state` | Market Regime `trend_regime.direction` |
|---|---|---|---|
| BULLISH | `bullish` | `bullish` | `bullish` |
| BEARISH | `bearish` | `bearish` | `bearish` |
| NEUTRAL | `sideways` | `range`, `transition` | `sideways` |

`alignment_analyzer.analyze()` computes `agreement_ratio` = (count of available engines matching the majority normalized direction) / (count of available engines). Engines with no data (§10 below) are excluded from both counts, not treated as a distinct "unknown" direction.

---

# 9. Conflict Detection (`conflict_analyzer.py`)

Four independently-testable rules, each returning a structured `ConflictEvidence` (never a bare string):

1. **Technical Analysis vs. SMC direction** - normalized directions are BULLISH vs. BEARISH. Severity HIGH.
2. **Market Regime internal misalignment** - `trend_regime.aligned is False`. Severity MEDIUM.
3. **Score quartile mismatch** - `|technical_score - smc_score| >= 50`. Severity MEDIUM.
4. **Market Regime vs. majority** - Technical Analysis and SMC's normalized directions agree with each other but Market Regime's opposes both. Severity LOW.

`penalty_for(conflicts)` sums `{LOW: -3, MEDIUM: -6, HIGH: -10}` per conflict, floored at `-15` (never more negative than the full `conflict_penalty` weight). `overall_severity(conflicts)` reports the single highest severity present, or `NONE` if the list is empty - exposed as the top-level `conflict_severity` field.

This is intentionally distinct from each upstream engine's own internal conflict analyzer (Technical Analysis's `ConflictAnalyzer`, SMC's `conflict_analyzer`, Market Regime's `conflict_analyzer` each detect conflicts *within* their own evidence) - this module detects disagreement *between* engines.

---

# 10. Data Quality & Freshness

**Data completeness** (`data_quality_analyzer.py`): six equally-weighted signals - each engine being unavailable (3 signals) and each engine reporting thin evidence when available (no support/resistance; no SMC structural events; Market Regime `UNCERTAIN`). Missing signals proportionally reduce the `data_completeness` component.

**Freshness** (`freshness_analyzer.py`): a `Timeframe -> timedelta` staleness-threshold table (`STALENESS_THRESHOLDS`), starting-point values not tuned against real request patterns. Timestamps are normalized to timezone-aware UTC before comparison (`_as_aware_utc`) - SQLite returns naive datetimes for `DateTime(timezone=True)` columns even when written UTC-aware (BACKLOG.md §9's documented gotcha), and `calculated_at` on every upstream result ultimately derives from a candle timestamp read through that path.

Freshness is intentionally low-weight (5 of 100): in this project's current architecture every engine is stateless-and-computed-on-demand (or, for SMC, persisted but always recomputed fresh per request) from stored candles, so freshness mostly reflects the market-data pipeline's own polling cadence, not something this engine controls.

---

# 11. Testing Strategy

| File | Covers |
|---|---|
| `test_analysis_confidence_direction_normalizer.py` | Exhaustive enum mapping |
| `test_analysis_confidence_alignment_analyzer.py` | All-agree, partial-agree, all-disagree, partial/full unavailability |
| `test_analysis_confidence_conflict_analyzer.py` | Each of the 4 rules individually, penalty flooring, severity aggregation |
| `test_analysis_confidence_data_quality_analyzer.py` | Each missing/thin-evidence signal, floor at 0 |
| `test_analysis_confidence_freshness_analyzer.py` | Fresh/stale boundary per timeframe, exact-boundary case, SQLite naive-datetime handling |
| `test_analysis_confidence_aggregator.py` | Full weighted sum, floor/cap, every level-band boundary |
| `test_analysis_confidence_summary_builder.py` | Sentence count, conflict/missing-data mentions, no AI-disclaimer language |
| `test_analysis_confidence_engine.py` | Integration with real Technical Analysis/SMC/Market Regime engines; TA/SMC-called-exactly-once regression; graceful degradation (partial and total); multi-timeframe |
| `test_analysis_confidence_api.py` | 200 path, graceful-degradation 200 (not 404), 404 on unknown asset, 422 on invalid timeframe, no-auth-required, multi-timeframe |
| `test_market_regime_engine.py` (extended) | Pre-computed TA/SMC params skip Market Regime's own internal calls |

Verified by inspection (every analyzer/rule/scenario has a dedicated test), consistent with Phases 4A-4C's practice - coverage tooling is not yet installed (BACKLOG.md §4).

---

# 12. Multi-Timeframe Strategy

Follows Market Regime's pattern (full `analyze()` per timeframe), not Technical Analysis's/SMC's lighter-weight summary pattern - a confidence result is itself a synthesis, so a "lightweight" multi-timeframe confidence summary would be a synthesis of a synthesis with no clear meaning. Reuses Market Regime's `_MULTI_TIMEFRAME_ORDER` tuple (W1/D1/H4/H1/M15).

Unlike Technical Analysis/SMC/Market Regime's multi-timeframe methods (which `continue` past timeframes with no candle data, omitting them from the result), `AnalysisConfidenceEngine.analyze_multi_timeframe()` always includes all five timeframes - because `analyze()` never raises (graceful degradation, §10 below), a timeframe with no data is itself confidence-relevant information (`VERY_LOW` + `missing_data`), not something to silently skip.

`ConfidenceMultiTimeframeVerdict.ALIGNED` only when every timeframe's `confidence_level` is `HIGH` or `VERY_HIGH`; otherwise `MIXED`.

---

# 13. Graceful Degradation

Any of the three upstream engines raising `ResourceNotFoundException` is caught in `AnalysisConfidenceEngine.analyze()` and converted to `None` + a `missing_data` entry, never propagated as a hard failure. This is a deliberate difference from Technical Analysis/SMC/Market Regime, which all 404 when no candles exist - a confidence result about "how much can we trust the current analysis" is itself meaningful even (especially) when the answer is "very little, because data is missing." See docs/15 §15.

---

# 14. API Contract

```
GET /analysis/confidence/{symbol}?timeframe=H1
GET /analysis/confidence/{symbol}/multi-timeframe
```

Public (no authentication), identical wiring convention to `/analysis/market-regime/*` (`get_asset_or_404` dependency, `Timeframe` query param, dependency-injected engine). 404 only for an unknown asset symbol - never for missing candle data (§13 above).

---

# 15. Out of Scope for Phase 4D

Same as docs/15 §17: any BUY/SELL/WAIT recommendation, News/Economic/Risk inputs (Phase 5/6), historical calibration, persistence of confidence results.

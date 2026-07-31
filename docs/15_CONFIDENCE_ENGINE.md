# Confidence Engine

Version: 2.0 (Phase 4D rewrite - supersedes v1.0's pre-Phase-4 vision text)

---

# 1. Objective

The Confidence Engine evaluates the QUALITY, COMPLETENESS, and CONSISTENCY of evidence already produced by the Technical Analysis, SMC, and Market Regime engines.

It does NOT determine whether to BUY or SELL. It does NOT predict whether a trade will win.

"Confidence" here means: *how trustworthy is the current analysis?* - never *probability this trade will win.* This distinction is explicit throughout this document and the implementation (ADR-031, ADR-043, ADR-047).

Every confidence score is explainable via a structured breakdown - no hidden calculations (docs/45 §9).

---

# 2. Responsibilities

The engine shall:

- Reframe Technical Analysis's, SMC's, and Market Regime's own scores into a common confidence axis, without recomputing their evidence
- Detect cross-engine directional agreement (alignment)
- Detect cross-engine contradictions (conflicts)
- Detect missing or thin evidence (data completeness)
- Detect stale evidence (freshness)
- Combine all of the above into one deterministic, explainable confidence result

---

# 3. Inputs

**Phase 4D (current):**

- Technical Analysis Engine (`technical_score`, `trend`, `support`/`resistance`, `warnings`, `calculated_at`)
- SMC Engine (`smc_score`, `market_structure.state`, structural evidence lists, `warnings`, `calculated_at`)
- Market Regime Engine (`confidence`, `regime`, `trend_regime`, `warnings`, `calculated_at`)

**Future inputs (Phase 5/6, not available yet):**

- News Sentiment Engine
- Economic Calendar Engine
- Risk Management Engine

These three do not exist in the codebase yet. The Confidence Engine's aggregation is deliberately modular (docs/45 §9, ADR-046) so they can be added as new weighted components without restructuring the aggregation pipeline - but they are out of scope for Phase 4D and must not be weighted for or referenced as available inputs until they are actually built.

---

# 4. Confidence Scale

Five bands over the 0-100 total (`confidence_level`), a starting point per the same "not tuned against real outcomes yet" caveat every prior scoring ADR carries:

| Range | Level |
|---|---|
| 80-100 | VERY_HIGH |
| 65-79 | HIGH |
| 45-64 | MODERATE |
| 25-44 | LOW |
| 0-24 | VERY_LOW |

---

# 5. Evidence Weighting

| Component | Weight |
|---|---|
| Technical Analysis alignment | 25 |
| SMC alignment | 25 |
| Market Regime confirmation | 20 |
| Cross-engine agreement | 20 |
| Data completeness | 5 |
| Freshness | 5 |
| Conflict penalty | -15 (floor) |

Market Regime is weighted lower than Technical Analysis/SMC individually because it is itself derived from Technical Analysis's and SMC's evidence (`MarketRegimeEngine.analyze()` calls both) - weighting it equally would double-count the same underlying evidence. See docs/45 §7 for the full algorithm and ADR-046 for the decision record.

---

# 6. Confidence Factors

**Increase confidence:**

- All three engines' directional evidence agree (bullish/bearish/neutral, normalized per docs/45 §5)
- High `technical_score`/`smc_score`/Market Regime `confidence`
- Complete evidence (support/resistance found, structural events detected, a qualifying regime candidate)
- Fresh evidence relative to the requested timeframe

**Decrease confidence:**

- Directional disagreement between engines
- Cross-engine conflicts (Technical Analysis vs. SMC direction, Market Regime's own internal trend/structure misalignment, sharply divergent scores, Market Regime opposing the Technical Analysis/SMC majority)
- Missing or thin evidence from any engine
- Stale evidence

Deliberately excluded from this list (docs/15 v1.0 included these, none are implementable yet): spread, liquidity, upcoming economic events, news sentiment. These require Phase 5/6 inputs that don't exist. Volatility is deliberately **not** an independent confidence factor here - Market Regime's `confidence_breakdown.volatility_clarity` already scores it, and it flows into this engine only via `regime_confirmation`; adding a second, independent volatility penalty here would double-count the same market condition (docs/45 §7).

---

# 7. Alignment Algorithm

Each engine's directional evidence is normalized onto a common `NormalizedDirection` axis (`bullish`/`bearish`/`neutral`) before comparison - Technical Analysis's `sideways`, SMC's `range`/`transition`, and Market Regime's `ranging` all normalize to `neutral` rather than being compared as unequal strings (docs/45 §5).

`agreement_ratio` = (count of available engines matching the majority direction) / (count of available engines reporting a direction). An engine with no data available (graceful degradation, §9 below) is excluded from both the numerator and denominator, not treated as a third possible direction.

---

# 8. Conflict Detection

Four deterministic, independently-testable rules (docs/45 §5, `app/services/analysis_confidence/conflict_analyzer.py`):

1. Technical Analysis trend directly contradicts SMC market structure (bullish vs. bearish) - HIGH severity.
2. Market Regime's own `trend_regime.aligned` is `False` (its internal trend/structure evidence disagree) - MEDIUM severity.
3. Technical Analysis's and SMC's scores diverge sharply (>= 50 points apart on their respective 0-100 scales) - MEDIUM severity.
4. Market Regime's direction opposes the Technical Analysis/SMC majority direction - LOW severity.

Each detected conflict contributes a fixed penalty by severity (LOW -3, MEDIUM -6, HIGH -10), summed and floored at -15 (the full `conflict_penalty` weight) - conflicts can never push overall confidence below the equivalent of "all evidence unavailable." An overall `conflict_severity` (`NONE`/`LOW`/`MEDIUM`/`HIGH`) reports the single highest severity found, for at-a-glance display.

---

# 9. Confidence Formula

```
Weighted component scores (Technical Analysis, SMC, Market Regime, Cross-Engine Agreement, Data Completeness, Freshness)
  + Conflict Penalty (<= 0, floored at -15)
  = Overall Confidence (floored at 0, capped at 100)
```

No "Agreement Bonus"/"Penalty Adjustments"/"Historical Calibration" pipeline (docs/15 v1.0 §9) - agreement is one weighted component among several, computed once, not a separate bonus stage. Historical Calibration remains a future enhancement only (§12 below) - it requires a persisted trade-outcomes dataset that does not exist and must not be implemented until real data is available to calibrate against.

---

# 10. Deterministic Summary

`summary` is a template-based, 2-3 sentence string built only from already-computed evidence (`app/services/analysis_confidence/summary_builder.py`) - no free-form language generation, no AI. It always states: the confidence level and score with the engine-agreement count, whether any cross-engine conflicts were detected, and (if present) a count and list of missing-data issues.

---

# 11. Transparency

Every response includes: `overall_confidence`, `confidence_level`, `summary`, the full `breakdown` (every weighted component), `alignment` (per-engine normalized direction and agreement ratio), `conflicts` (structured, not bare strings) with `conflict_severity`, `missing_data`, and `warnings` (forwarded from every available upstream engine). No hidden calculations.

---

# 12. Future Enhancements

- News Sentiment / Economic Calendar / Risk Management as additional weighted components (Phase 5/6) - the aggregation pipeline (docs/45 §9, ADR-046) is designed to accept these without restructuring
- Historical calibration (comparing a current setup against historical outcomes) - blocked on a persisted trade-outcomes dataset that does not exist yet; must not be implemented speculatively
- Market regime-specific confidence weighting adjustments, once real outcomes exist to inform tuning

---

# 13. Persistence

Fully stateless (ADR-045) - no new table, recomputed fresh on every request from Technical Analysis, SMC, and Market Regime, mirroring ADR-027 (Technical Analysis) and ADR-038 (Market Regime) rather than SMC's persisted-mutable-events pattern (ADR-032/033). There is no "genuinely evolving single entity" here to justify persistence (BACKLOG.md §13's criterion) - a confidence result is a derived snapshot of three other engines' current state.

---

# 14. API

```
GET /analysis/confidence/{symbol}?timeframe=
GET /analysis/confidence/{symbol}/multi-timeframe
```

Public (no authentication), matching every other `/analysis/*` endpoint's convention. See docs/04 §"Confidence" and docs/33 for the full contract. Unlike Technical Analysis/SMC/Market Regime, missing candle data for one upstream engine does **not** produce a 404 - the Confidence Engine degrades gracefully (§15 below) and still returns a 200 with reduced confidence and an explicit `missing_data` entry. A 404 is only returned when the asset symbol itself is unknown.

---

# 15. Graceful Degradation

If Technical Analysis, SMC, or Market Regime raises `ResourceNotFoundException` (e.g. no candles for that asset/timeframe), that engine's evidence is treated as unavailable (`None`), recorded in `missing_data` (e.g. `"technical_analysis_unavailable"`), and confidence is still computed from whatever evidence remains. If all three are unavailable, the result is still a valid, fully-transparent `ConfidenceResult` with `confidence_level = VERY_LOW`, never an opaque failure.

---

# 16. Testing

Every analyzer, aggregation rule, and API path has a dedicated test (`app/services/analysis_confidence/`'s test suite) - verified by inspection, consistent with this project's practice for Phases 4A-4C (coverage tooling is not yet installed, per BACKLOG.md §4). See docs/45 §11 for the full test list.

---

# 17. Out of Scope for Phase 4D

- Any BUY/SELL/WAIT recommendation or trade-outcome prediction (ADR-031, ADR-043, ADR-047)
- News Sentiment, Economic Calendar, Risk Management inputs (Phase 5/6, not built)
- Historical calibration / trade-outcome comparison (needs a dataset that doesn't exist)
- Persistence of confidence results (ADR-045)

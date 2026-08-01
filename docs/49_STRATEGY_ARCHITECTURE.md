# Strategy Architecture

# 1. Scope

Phase 5D's `StrategyEngine` (`app/services/strategy_engine.py`) evaluates which of seven trading strategy *methodologies* fits current market evidence for a given asset/timeframe - it never generates a BUY/SELL/WAIT recommendation itself (docs/17 §1, ADR-031/ADR-043 extended, ADR-069). It classifies strategy compatibility only; a specific trade setup is a future Signal Engine's job (Phase 6).

`MarketRegimeEngine` itself is unchanged (ADR-069) - ADR-043 stands exactly as written. This engine is the consumer ADR-043's Future Review note anticipated, built as its own dedicated Phase 5D engine rather than retrofitted onto `MarketRegimeEngine`.

See docs/17_STRATEGY_ENGINE.md for the product-level vision this document implements.

---

# 2. Statelessness (ADR-070)

Fully stateless, mirroring Risk Management (ADR-063) and the Confidence Engine (ADR-045) - no new table (docs/03 reserves none for this engine). Every `evaluate()` call recomputes fresh.

---

# 3. Reuse Map (ADR-071)

| docs/17 input/requirement | Reused from |
|---|---|
| Market Regime, Technical Analysis, SMC, Confidence Score | `AnalysisConfidenceEngine.analyze()` - one call yields `.technical`, `.smc`, `.market_regime`, `.overall_confidence` |
| Risk Management Engine (docs/17 §3) | **Not** `RiskManagementEngine.evaluate()` (needs a candidate trade setup this engine doesn't have, ADR-062) - instead, `app.services.risk_management`'s `session_classifier.classify()`, `liquidity_filter.classify()`, `economic_filter.analyze()` directly, plus `.market_regime.volatility.state` (ADR-071) |
| Market Session (docs/17 §3) | `risk_management.session_classifier.classify(now)` |
| Economic Events | `EconomicCalendarEngine.list_events(currency=..., start=..., end=...)` |

No bespoke re-derivation of anything Phase 4A-4C/5C already computes.

---

# 4. Buildable Strategy Set (ADR-072)

Seven strategies implemented; **Momentum Trading is not implemented** (no requirements defined anywhere in docs/17). "Range Trading" and "Mean Reversion" (docs/17 §4) are merged into one `MEAN_REVERSION` strategy (docs/17 never defines them separately).

| `StrategyName` | Compatible `MarketRegimeState` set | Preferred `Timeframe`s |
|---|---|---|
| `TREND_FOLLOWING` | `{TRENDING_BULLISH, TRENDING_BEARISH}` | H1, H4, D1 |
| `SMC` | `{TRENDING_BULLISH, TRENDING_BEARISH, ACCUMULATION, DISTRIBUTION}` (resolves docs/17 §8's undefined "Institutional Trend," ADR-072) | M15, H1, H4 |
| `BREAKOUT` | `{BREAKOUT}` | H1, H4, D1 |
| `PULLBACK` | `{PULLBACK, TRENDING_BULLISH, TRENDING_BEARISH}` | H1, H4 |
| `MEAN_REVERSION` | `{RANGING}` | H1, H4 |
| `SCALPING` | `{TRENDING_BULLISH, TRENDING_BEARISH, RANGING, BREAKOUT}` (session/liquidity-gated, not regime-specific per docs/17 §12) | M1, M5 |
| `SWING_TRADING` | `{TRENDING_BULLISH, TRENDING_BEARISH, ACCUMULATION, DISTRIBUTION}` | H4, D1, W1 |

---

# 5. Requirements Checklists (Evidence Quality, ADR-074)

Each strategy's `app/services/strategy/requirements/<name>.py` checks its docs/17-specified requirements against the shared evidence bundle, returning `(met_count, total_count)`. Requirements with no data source (Spread for Scalping, R:R for Swing Trading) are excluded from `total_count` entirely (ADR-074) - never fabricated.

| Strategy | Requirements checked (docs/17 source section) |
|---|---|
| Trend Following (§7) | EMA alignment (`trend_evidence.moving_average.bullish_alignment`/`.bearish_alignment`), strong ADX (`trend_evidence.adx >= 25`), healthy volume (`volume.relative_volume_state == ABOVE_AVERAGE`), high confidence (`overall_confidence >= 65`) |
| SMC (§8) | Order block present (`smc.order_blocks` non-empty, ACTIVE), BOS present (`smc.bos` non-empty), CHOCH present (`smc.choch` non-empty), liquidity sweep present (`smc.liquidity_sweeps` non-empty), FVG present (`smc.fair_value_gaps` non-empty) |
| Breakout (§9) | Resistance/support break (`market_regime.breakout.detected`), volume confirmation (`.volume_confirmed`), momentum increase (`technical.momentum.macd_bullish` or `.momentum_positive`), healthy volatility (`market_regime.volatility.state` in {NORMAL, HIGH}) |
| Pullback (§10) | Strong trend (`trend_evidence.strength` in {STRONG, VERY_STRONG}), temporary retracement (`market_regime.pullback_reversal.pullback_depth == HEALTHY`), support holds (`technical.support` present), momentum recovery (`market_regime.pullback_reversal.reversal_confidence` present and above a floor) |
| Mean Reversion (§11) | Range market (`market_regime.range.is_ranging`), strong support (`technical.support.strength` in {moderate, strong}), strong resistance (`technical.resistance.strength` in {moderate, strong}), low trend strength (`trend_evidence.strength` in {WEAK, MODERATE}) |
| Scalping (§12) | High liquidity (`risk_management.liquidity_filter.classify(...)` in {HIGH, EXCELLENT}), fast momentum (`technical.momentum.momentum_positive` is not None), no high-impact news (`risk_management.economic_filter.analyze(...).hard_reject is False` and no HIGH-in-window event) — Low Spread excluded (no data source, ADR-074) |
| Swing Trading (§13) | Higher-timeframe trend present (`trend_evidence.strength` in {STRONG, VERY_STRONG}, evaluated on the requested timeframe - not a separate higher-timeframe fetch, out of scope §8), strong structure (`smc.market_structure.state` in {BULLISH, BEARISH}), medium volatility (`market_regime.volatility.state == NORMAL`) — Healthy RR excluded (no candidate setup, ADR-074) |

---

# 6. Market Match (ADR-073)

```
if current_regime not in strategy.compatible_regimes:
    market_match = 0
elif timeframe in strategy.preferred_timeframes:
    market_match = 30
else:
    market_match = 20
```

A regime-incompatible strategy (`market_match = 0`) still has its other components computed (never short-circuited) - matches docs/17 §15's own worked example where a mismatched strategy scores a nonzero total.

---

# 7. Strategy Score (docs/17 §14, 100 points)

| Component | Weight | Source |
|---|---|---|
| `market_match` | 30 | §6 above |
| `evidence_quality` | 25 | `25 * met_count / total_count` from §5's checklist |
| `confidence` | 20 | `overall_confidence / 100 * 20` |
| `risk` | 15 | Derived from session/liquidity/economic-event/volatility evidence (ADR-071): starts at 15, -3 if session is `CLOSED`, -3 if liquidity is LOW, -5 if a CRITICAL economic event is in its risk window, -3 if volatility is EXTREME; floored at 0 |
| `historical_performance` | 10 | Uniform 5/10 placeholder (ADR-075) - no data source exists yet |

`total` = sum of all five, clamped 0-100.

---

# 8. Ranking & Rejection (ADR-076)

A strategy is **rejected** if `market_match == 0` OR `total < 50`. Every rejected strategy carries an explicit reason string. Among non-rejected strategies: `primary_strategy` = highest `total`; `alternative_strategies` = the rest, ranked descending. Ties broken by `StrategyName`'s declaration order (deterministic).

---

# 9. Historical Performance Placeholder (ADR-075)

Uniform 5/10 for every strategy - no trade-outcomes/backtest dataset exists anywhere in this project (mirrors docs/15 v1.0 §10's Confidence Engine precedent). Every strategy's ceiling is therefore 95/100 until a real dataset exists.

---

# 10. Testing Strategy

| File | Covers |
|---|---|
| `test_strategy_market_match.py` | Full/partial/zero match per regime+timeframe combination |
| `test_strategy_historical_performance.py` | Uniform placeholder for every strategy |
| `test_strategy_requirements_*.py` (7 files) | Each strategy's checklist, met/unmet per requirement, ungateable-requirement exclusion |
| `test_strategy_scorer.py` | Full aggregation, floor/cap, risk-component penalty stacking |
| `test_strategy_ranking.py` | Market-Match-0 rejection, sub-50 rejection, primary/alternative split, deterministic tie-break |
| `test_strategy_engine.py` | Integration against real `AnalysisConfidenceEngine`/`EconomicCalendarEngine` on a seeded SQLite session |
| `test_strategy_routes.py` | `GET /strategy/evaluate/{symbol}` response shape, 404 on unknown asset, no-auth-required |

Verified by inspection, consistent with Phase 5A-5C's practice - coverage tooling is still not installed (BACKLOG.md §4).

---

# 11. Out of Scope for Phase 5D

Momentum Trading (undefined requirements, ADR-072); User Custom/AI Generated strategies (docs/17 §4's own "Future Strategies"); persistence of evaluations (stateless, ADR-070); any BUY/SELL/trade-level recommendation; AI-generated explanation of strategy selection (docs/17 §18, Phase 6's job); a true multi-timeframe scan for Swing Trading's "Higher Timeframe Trend" (uses the requested timeframe's own evidence); Confidence Engine integration in the reverse direction (ADR-047's boundary); real historical/backtest-based strategy performance (ADR-075).

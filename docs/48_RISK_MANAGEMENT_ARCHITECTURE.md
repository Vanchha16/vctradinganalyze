# Risk Management Architecture

# 1. Scope

Phase 5C's `RiskManagementEngine` (`app/services/risk_management_engine.py`) evaluates whether a caller-supplied candidate trade setup is safe enough to approve - it never generates a BUY/SELL/WAIT recommendation itself (docs/12 §1, ADR-031/ADR-043 extended, ADR-062). It evaluates a setup passed directly in the request, not a persisted `Signal` (ADR-062, since no Signal Engine exists yet).

Not wired into `AnalysisConfidenceEngine` in the reverse direction - ADR-047 reserved that integration (Risk Management as one of *Confidence's* weighted components) for a future ADR. This engine instead *calls* `AnalysisConfidenceEngine` downstream (§3).

See docs/12_RISK_MANAGEMENT_ENGINE.md for the product-level vision this document implements.

---

# 2. Statelessness (ADR-063)

Fully stateless, mirroring the Confidence Engine (ADR-045) - no new table (docs/03 reserves none for this engine; `risk_level`/`risk_reward` live on future `ai_analysis`/`signals` tables, Phase 6/7). Every `evaluate()` call recomputes fresh. docs/12 §18's logging requirement is satisfied by structured `structlog` logging, not persistence.

---

# 3. Reuse Map (ADR-064)

| docs/12 input | Reused from | Field |
|---|---|---|
| Technical Score | `AnalysisConfidenceEngine.analyze()` → `.technical` | `TechnicalAnalysisResult.technical_score` |
| Trend Quality | same | `.strength` (`TrendStrengthLevel`: WEAK/MODERATE/STRONG/VERY_STRONG) |
| SMC Score | same → `.smc` | `SMCAnalysisResult.smc_score` |
| Order Blocks / Liquidity Zones (stop-loss validation) | same | `.order_blocks`, `.liquidity_zones` |
| **Volatility** | same → `.market_regime` | `MarketRegimeResult.volatility.state` (`VolatilityRegimeState`: VERY_LOW/LOW/NORMAL/HIGH/EXTREME) - exact match for docs/12 §6 |
| Confidence Score | `AnalysisConfidenceEngine.analyze()` | `.overall_confidence` |
| News Score | `NewsSentimentEngine.get_sentiment_for_asset(symbol, since)` | `NewsSentimentResult.articles` |
| Economic Events / risk window | `EconomicCalendarEngine.list_events(currency=..., start=..., end=...)` | `EconomicEventEvidence.risk_window`/`.importance` |
| Current Price, ATR | `PriceCandleRepository.get_latest`, `.volatility.atr` (via Confidence Engine's `.technical`) | — |

No bespoke re-derivation of volatility or trend classification (ADR-064).

---

# 4. Data Flow

Single-call aggregation - no ingest/read split like News/Economic, since nothing is persisted:

```
RiskManagementEngine.evaluate(asset, timeframe, direction, entry_price, stop_loss, take_profit, spread=None)
  -> AnalysisConfidenceEngine.analyze(asset, timeframe)              [-> technical, smc, market_regime, overall_confidence]
  -> NewsSentimentEngine.get_sentiment_for_asset(asset.symbol, since=24h ago)
  -> EconomicCalendarEngine.list_events(currency={base,quote}, start=now-2h, end=now+24h)
  -> session_classifier.classify(now)
  -> spread_filter.classify(spread, entry_price)                     [skipped if spread is None]
  -> liquidity_filter.classify(latest_candle.volume, recent_avg_volume)
  -> correlation_analyzer.analyze(asset, timeframe)                  [fixed curated pairs]
  -> economic_filter.analyze(economic_events)
  -> risk_reward_validator.validate(entry_price, stop_loss, take_profit)
  -> stop_loss_validator.validate(entry_price, stop_loss, atr, order_blocks, liquidity_zones)
  -> trade_quality_aggregator.aggregate(trend_quality, technical, smc, risk_penalties, news, economic)
  -> decision.decide(hard_reject_checks, trade_quality)              [ADR-068]
  -> RiskEvaluation
```

---

# 5. Rule Tables

**Session Classifier** (`session_classifier.py`, docs/12 §5) - UTC hour bands, checked in order (overlap first); weekend closure (Friday 22:00 UTC - Sunday 22:00 UTC) checked before hour bands, approximating real forex market hours since this project has no holiday-calendar data (ADR-066):

| Condition | `MarketSession` |
|---|---|
| Saturday (any hour), or Sunday before 22:00 UTC, or Friday from 22:00 UTC | `CLOSED` |
| 13:00–17:00 UTC | `LONDON_NEW_YORK_OVERLAP` (highest priority) |
| 08:00–17:00 UTC | `LONDON` |
| 13:00–22:00 UTC | `NEW_YORK` |
| 00:00–09:00 UTC | `ASIAN` |
| 22:00–07:00 UTC (wraps midnight) | `SYDNEY` |

**Spread Filter** (`spread_filter.py`, docs/12 §7, ADR-065) - `spread_ratio = spread / entry_price`, skipped entirely if `spread` is `None`:

| `spread_ratio` | Classification | Effect |
|---|---|---|
| < 0.02% | Excellent | none |
| 0.02%–0.05% | Acceptable | none |
| 0.05%–0.15% | High | Risk component -3 |
| > 0.15% | Extreme | Hard reject |

**Liquidity Filter** (`liquidity_filter.py`, docs/12 §10, ADR-066) - latest candle volume vs. its own trailing 20-candle average; `UNKNOWN` if volume is `None`:

| Volume ratio | Classification | Effect |
|---|---|---|
| < 0.5x | Low | Risk component -3 |
| 0.5x–1.5x | Normal | none |
| 1.5x–3x | High | none |
| > 3x | Excellent | none |
| volume unavailable | Unknown | Risk component -1 |

**Correlation Filter** (`correlation_analyzer.py`, docs/12 §9, ADR-067) - Pearson correlation of close-price returns over the last 100 candles, fixed curated pairs only (EURUSD↔GBPUSD, XAUUSD↔XAGUSD, BTCUSD↔ETHUSD); skipped if the counterpart asset isn't seeded:

| \|correlation\| | Effect |
|---|---|
| > 0.85 | Risk component -2 per flagged pair (floor -4 total), `warnings` entry - **never a hard reject** |
| ≤ 0.85 | none |

**Economic Filter** (`economic_filter.py`, docs/12 §8) - reuses `EconomicEventEvidence.risk_window`/`.importance` directly (Phase 5B), driving event = highest-urgency match among events for the asset's base/quote currency:

| Driving event | Effect |
|---|---|
| `CRITICAL` importance, `risk_window=True` | Hard reject |
| `HIGH` importance, `risk_window=True` | Economic component capped at 4/10 |
| `MEDIUM` importance present (any timing, in scan window) | Economic component capped at 7/10 |
| none of the above | Economic component = 10/10 |

---

# 6. Risk/Reward & Stop-Loss Validation (docs/12 §12/§13)

```
reward = abs(take_profit - entry_price)
risk   = abs(entry_price - stop_loss)
rr     = reward / risk
```

| `rr` | Classification | Effect |
|---|---|---|
| < 2.0 | Below minimum | Hard reject |
| 2.0–2.99 | Good (meets minimum) | none |
| 3.0–3.99 | Very Good (preferred) | none |
| ≥ 4.0 | Excellent | none |

Stop-loss distance (`stop_loss_validator.py`): `atr_ratio = abs(entry_price - stop_loss) / atr` (when ATR is available from `.technical.volatility.atr`) - `atr_ratio < 0.5` is an unrealistically tight stop, **hard reject**. Additionally, informational-only (never a reject, per docs/12 §13's own softer "check" framing): if `stop_loss` falls within an active (`SMCEventStatus.ACTIVE`) `OrderBlockEvidence`'s `[zone_low, zone_high]`, or is close to an active `LiquidityZoneEvidence.level`, a `warnings` entry notes it - reusing SMC's already-computed structure rather than a new structural-invalidation algorithm docs/12 doesn't fully specify.

---

# 7. Trade Quality Score (docs/12 §15, 100 points)

| Component | Weight | Source |
|---|---|---|
| `trend_quality` | 20 | `TrendStrengthLevel` mapped: WEAK=5, MODERATE=12, STRONG=17, VERY_STRONG=20 |
| `technical` | 20 | `technical_score / 100 * 20` |
| `smc` | 20 | `smc_score / 100 * 20` |
| `risk` | 20 | Starts at 20, minus §5's spread/liquidity/correlation penalties and a minor -1 for non-overlap Asian/Sydney sessions, floored at 0 |
| `news` | 10 | 5 (neutral) if no recent news; adjusted toward 10 if recent sentiment direction agrees with `direction`, toward 0 if it opposes |
| `economic` | 10 | Per §5's Economic Filter table |

`trade_quality` = sum of all six components, clamped 0-100 (mirrors `ConfidenceBreakdown.total`'s floor/cap convention, ADR-028/036/042/046 lineage).

---

# 8. Decision Matrix & Hard-Reject Precedence (ADR-068)

Hard-reject rules (§5/§6's "Hard reject" rows, plus session `CLOSED`) are evaluated first and independently of the score. **Every** triggered reason is collected into `rejected_reasons` (not first-match) - `approved=False` if that list is non-empty. `trade_quality` is always computed regardless (explainability, ADR-041's precedent extended).

If no hard-reject rule triggers, docs/12 §16's score tier applies:

| `trade_quality` | Tier |
|---|---|
| 90+ | Excellent |
| 80–89 | Very Good |
| 70–79 | Good |
| 60–69 | Average |
| < 60 | Reject (`approved=False`, score-based, not a "hard-reject rule" reason) |

`risk_level` (docs/12 §17): `LOW` if volatility is VERY_LOW/LOW and tier is Excellent/Very Good; `HIGH` if volatility is HIGH/EXTREME or tier is Average/Reject; `MEDIUM` otherwise.

---

# 9. Position Sizing Guidance (docs/12 §14)

No lot-size calculation (explicitly excluded by docs/12 §14) - guidance only:

| Condition | Guidance |
|---|---|
| Rejected (either hard-reject or score < 60) | none (`null`) |
| Tier Excellent AND `risk_level` LOW | Aggressive (high confidence only) |
| Tier Excellent or Very Good (otherwise) | Normal |
| Tier Good | Conservative |
| Tier Average | Very Conservative |

Hand-tuned starting point, not empirically calibrated - same caveat as every prior scoring table (ADR-028/030/035/036/037/042/046/055/059/060).

---

# 10. Not Timeframe-Only Scoped

Unlike News/Economic Calendar (no `timeframe` at all) but also unlike Phase 4's pure `analyze(asset, timeframe)` engines, this engine takes `timeframe` **plus** a full candidate setup (direction, entry, stop, target, optional spread) - it evaluates one specific hypothesis, not a general asset/timeframe query.

---

# 11. Testing Strategy

| File | Covers |
|---|---|
| `test_risk_session_classifier.py` | Every session boundary, weekend `CLOSED`, overlap priority |
| `test_risk_spread_filter.py` | Each band, `None` skip path |
| `test_risk_liquidity_filter.py` | Each band, `None` volume → `UNKNOWN` |
| `test_risk_correlation_analyzer.py` | Each curated pair, threshold boundary, missing-counterpart skip |
| `test_risk_reward_validator.py` | Each R:R band, below-minimum reject |
| `test_risk_stop_loss_validator.py` | ATR-ratio reject boundary, order-block/liquidity-zone informational warnings |
| `test_risk_trade_quality_aggregator.py` | Every component, floor/cap |
| `test_risk_decision.py` | Every hard-reject rule individually, multiple-simultaneous-reasons collection, score-tier fallback, position-sizing mapping |
| `test_risk_management_engine.py` | Integration against real `AnalysisConfidenceEngine`/`NewsSentimentEngine`/`EconomicCalendarEngine` on a seeded SQLite session |
| `test_risk_management_routes.py` | `POST /risk/evaluate` approve/reject paths, 404 on unknown asset, no-auth-required |

Verified by inspection, consistent with Phase 5A/5B's practice - coverage tooling is still not installed (BACKLOG.md §4).

---

# 12. Out of Scope for Phase 5C

Persistence of evaluations (stateless, ADR-063); position-size-in-lots calculation (docs/12 §14); Signal Engine / AI Orchestrator integration (don't exist yet); Confidence Engine integration in the reverse direction (ADR-047's reserved weight-rebalancing); true liquidity/order-book data (volume-ratio proxy only, ADR-066); true holiday-calendar detection (weekend-based Market-Close approximation only, ADR-066); portfolio-level/daily/weekly exposure limits, Monte Carlo simulation, AI risk calibration (docs/12 §20); a general market-wide correlation model (fixed curated pair list only, ADR-067).

# Economic Calendar Engine

Version: 1.1

Implementation (Phase 5B): docs/47_ECONOMIC_CALENDAR_ARCHITECTURE.md, ADR-056 through ADR-061.

---

# 1. Objective

The Economic Calendar Engine collects, validates, and analyzes macroeconomic events that influence financial markets.

It does NOT generate BUY or SELL recommendations.

Its purpose is to provide structured macroeconomic evidence to the AI Orchestrator.

---

# 2. Responsibilities

The engine shall:

- Fetch economic events
- Classify event importance
- Compare actual vs forecast
- Calculate market bias
- Detect upcoming risk windows
- Detect central bank events
- Publish structured evidence

---

# 3. Supported Events

Inflation

- CPI
- Core CPI
- PPI
- Core PPI

Employment

- Non-Farm Payroll (NFP)
- Unemployment Rate
- Average Hourly Earnings
- Jobless Claims

Growth

- GDP
- Retail Sales
- PMI
- Industrial Production

Central Banks

- FOMC
- Interest Rate Decision
- ECB
- BOE
- BOJ
- RBA
- RBNZ
- BOC
- SNB

Consumer

- Consumer Confidence
- Consumer Sentiment

Housing

- Building Permits
- Housing Starts
- Existing Home Sales

Other

- Trade Balance
- Current Account
- Manufacturing PMI
- Services PMI

---

# 4. Event Importance

Critical

Examples

FOMC

Interest Rate Decision

NFP

CPI

GDP

High

PMI

Retail Sales

Consumer Confidence

Medium

Housing

Trade Balance

Low

Minor reports

---

# 5. Event Lifecycle

Fetch

↓

Validate

↓

Normalize

↓

Compare Forecast

↓

Calculate Surprise

↓

Determine Bias

↓

Store

↓

Publish Evidence

---

# 6. Surprise Calculation

Example

Forecast

3.2%

Actual

2.8%

Previous

3.5%

Surprise

-0.4%

Store

Magnitude

Direction

Confidence

---

# 7. Market Bias

Examples

Lower CPI

↓

Potentially weaker USD

↓

Potentially stronger Gold

↓

Potentially stronger Equities

Higher CPI

↓

Potentially stronger USD

↓

Potentially weaker Gold

↓

Potentially weaker Equities

The engine stores the potential impact rather than guaranteeing market direction.

---

# 8. Pre-Event Risk Window

Critical Event

30 minutes before

↓

High Risk

Critical Event

30 minutes after

↓

High Risk

High Impact Event

60 minutes before

↓

Medium Risk

---

# 9. Output Format

{
  "event": "US CPI",
  "importance": "Critical",
  "forecast": 3.2,
  "actual": 2.8,
  "previous": 3.5,
  "surprise": -0.4,
  "market_bias": {
    "USD": "Potentially Bearish",
    "Gold": "Potentially Bullish",
    "NASDAQ": "Potentially Bullish"
  },
  "risk_window": true
}

`risk_window` is **computed at read time** from `(now, release_time, importance)`, never stored (docs/47 §7, ADR-061) - it changes continuously as real time passes, so persisting it would go stale the instant it was written.

---

# 10. AI Rules

The AI must never:

Invent economic events

Invent forecasts

Invent actual values

Ignore upcoming critical releases

---

# 11. Risk Rules

If a critical event is within the configured risk window:

- Reduce confidence
- Warn the user
- Recommend WAIT when appropriate

**Not implemented by this engine (Phase 5B).** The Economic Calendar Engine exposes `risk_window: bool` as structured evidence only (docs/47 §7) - confidence reduction, user warnings, and WAIT recommendations are a future Risk Engine's/AI Orchestrator's responsibility to derive from this evidence, consistent with this project's no-recommendation principle for every deterministic engine (ADR-031, ADR-043, extended here).

---

# 12. Logging

Store

Event

Country

Currency

Importance

Forecast

Actual

Previous

Surprise

Execution Time

---

# 13. Testing

Validate:

Forecast comparison

Surprise calculation

Bias generation

Risk windows

Coverage target: 95%

---

# 14. Future Enhancements

Market reaction models

Historical event database

Expected volatility estimation

Cross-country event correlation

AI-generated macro summaries
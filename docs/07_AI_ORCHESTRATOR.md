# AI Orchestrator

Version: 1.1

Implementation (Phase 6A): docs/50_AI_ORCHESTRATOR_ARCHITECTURE.md, ADR-077 through ADR-084. Implemented as a single `AIOrchestratorEngine` class combining this document's "orchestration" role with docs/13's "reasoning" role (ADR-077) - §3's "AI Reasoning Engine" pipeline step and §7's "AI Explanation" priority-list entry both refer to that one component. §11's "confidence is calculated from evidence" is implemented as: confidence is never calculated by this phase at all - it is reused verbatim from `AnalysisConfidenceEngine` (Phase 4D, ADR-079); this document's "calculate" language predates that resolution.

---

# 1. Objective

The AI Orchestrator is the central coordinator of the platform.

It does NOT analyze the market itself.

Instead, it collects information from specialized engines and produces one final market analysis.

The orchestrator acts as the "brain" of the system.

---

# 2. Responsibilities

The orchestrator shall:

- Collect market data
- Validate input
- Trigger analysis engines
- Combine results
- Calculate confidence
- Detect conflicting signals
- Generate final recommendation
- Store analysis
- Notify downstream services

---

# 3. Analysis Pipeline

Market Data
        │
        ▼
Technical Analysis Engine
        │
        ▼
Smart Money Engine
        │
        ▼
News Sentiment Engine
        │
        ▼
Economic Calendar Engine
        │
        ▼
Risk Engine
        │
        ▼
AI Reasoning Engine
        │
        ▼
Confidence Engine
        │
        ▼
Signal Engine
        │
        ▼
Database
        │
        ▼
Dashboard
        │
        ▼
Telegram

---

# 4. Input

Asset

Example

EURUSD

Timeframe

M15

M30

H1

H4

Daily

Current Price

Indicators

Market Structure

Economic Events

News Sentiment

Volume

Volatility

---

# 5. Output

Recommendation

BUY

SELL

WAIT

Confidence Score

Risk Level

Entry

Stop Loss

Take Profit

Risk Reward Ratio

Reasoning

Warnings

---

# 6. Decision Flow

Receive market snapshot

↓

Validate data

↓

Run Technical Engine

↓

Run SMC Engine

↓

Run News Engine

↓

Run Economic Engine

↓

Run Risk Engine

↓

Generate AI explanation

↓

Calculate confidence

↓

Create signal

↓

Store analysis

↓

Notify users

---

# 7. Engine Priority

1

Risk Engine

Highest Priority

2

Economic Engine

3

SMC Engine

4

Technical Engine

5

News Sentiment

6

AI Explanation

---

# 8. Failure Handling

If one engine fails:

Continue if safe.

Example

News unavailable.

Technical Analysis available.

System still produces analysis.

If critical engines fail:

No signal generated.

Return explanation.

---

# 9. AI Guardrails

The AI must never:

Invent prices

Invent indicators

Invent news

Invent economic events

Invent confidence

Invent trend direction

All conclusions must reference actual analysis results.

---

# 10. Explainability

Every recommendation must include:

Technical reasons

SMC reasons

News impact

Economic impact

Risk explanation

Confidence explanation

---

# 11. Confidence Calculation

Confidence is calculated from evidence.

It is NOT generated randomly.

Example factors:

Trend alignment

SMC confirmation

Indicator agreement

News sentiment

Economic impact

Volatility

Liquidity

Risk level

---

# 12. Logging

Every analysis run stores:

Execution time

Input

Output

Confidence

Errors

Warnings

AI reasoning

---

# 13. Future Extensions

Portfolio AI

Multi-agent collaboration

Strategy optimization

Backtesting integration

Learning engine

Personalized recommendations
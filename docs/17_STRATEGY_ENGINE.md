# Strategy Engine

Version: 1.1

Implementation (Phase 5D): docs/49_STRATEGY_ARCHITECTURE.md, ADR-069 through ADR-076.

---

# 1. Objective

The Strategy Engine selects, evaluates, and manages trading strategies based on the current market regime and available evidence.

It does NOT directly generate BUY or SELL signals.

Instead, it determines which strategy (or strategies) are valid under current market conditions and provides structured recommendations to the Signal Engine.

---

# 2. Responsibilities

The engine shall:

- Evaluate available strategies
- Check strategy requirements
- Match strategies to market regime
- Score strategy quality
- Reject invalid strategies
- Publish strategy evidence

---

# 3. Inputs

Market Regime Engine

Technical Analysis Engine

SMC Engine

Risk Management Engine

Confidence Engine

Current Asset

Current Timeframe

Market Session

---

# 4. Supported Strategies

Trend Following

Smart Money Concepts (SMC)

Breakout

Pullback

Range Trading / Mean Reversion

Scalping

Swing Trading

Momentum Trading

Future Strategies

User Custom Strategies

AI Generated Strategies

**Implementation note (Phase 5D, ADR-072):** "Range Trading" and "Mean Reversion" were never defined as separate strategies anywhere in this document - §11 describes one strategy under both names, implemented as a single `MEAN_REVERSION` strategy. "Momentum Trading" has no requirements defined anywhere in this document and is **not implemented** in Phase 5D - inventing requirements for it would be architecture invention, not implementation. Seven strategies are implemented: Trend Following, SMC, Breakout, Pullback, Mean Reversion, Scalping, Swing Trading.

---

# 5. Strategy Selection Flow

Receive Market Evidence

↓

Identify Market Regime

↓

Find Compatible Strategies

↓

Validate Risk

↓

Score Strategy

↓

Rank Strategies

↓

Publish Results

---

# 6. Strategy Definition

Each strategy contains:

Name

Description

Required Market Regime

Minimum Confidence

Minimum Trade Quality

Required Indicators

Required SMC Signals

Risk Limits

Recommended Timeframes

---

# 7. Trend Following Strategy

Best Market

Trending Bullish

Trending Bearish

Requirements

EMA Alignment

Strong ADX

Healthy Volume

High Confidence

Preferred Timeframes

H1

H4

Daily

---

# 8. Smart Money Strategy

Best Market

Institutional Trend

**Implementation note (Phase 5D, ADR-072):** "Institutional Trend" is not a defined `MarketRegimeState` value (docs/16 §3's eleven values). Resolved to `{Trending Bullish, Trending Bearish, Accumulation, Distribution}` - the regime values most consistent with SMC's own structural-trend and accumulation/distribution vocabulary (docs/49 §4).

Requirements

Order Block

Break of Structure

CHOCH

Liquidity Sweep

Fair Value Gap

Preferred Timeframes

M15

H1

H4

---

# 9. Breakout Strategy

Requirements

Resistance Break

Volume Confirmation

Momentum Increase

Healthy Volatility

---

# 10. Pullback Strategy

Requirements

Strong Trend

Temporary Retracement

Support Holds

Momentum Recovery

---

# 11. Mean Reversion

Requirements

Range Market

Strong Support

Strong Resistance

Low Trend Strength

---

# 12. Scalping

Requirements

Low Spread

High Liquidity

Fast Momentum

No High Impact News

Preferred Timeframes

M1

M5

---

# 13. Swing Trading

Requirements

Higher Timeframe Trend

Strong Structure

Healthy RR

Medium Volatility

Preferred Timeframes

H4

Daily

Weekly

---

# 14. Strategy Scoring

Maximum Score

100

Components

Market Match

30

Evidence Quality

25

Confidence

20

Risk

15

Historical Performance

10

---

# 15. Strategy Ranking

Example

Trend Following

94

SMC

91

Pullback

82

Breakout

78

Mean Reversion

42

---

# 16. Strategy Recommendation

Primary Strategy

Trend Following

Alternative Strategy

Pullback

Rejected

Mean Reversion

Reason

Market strongly trending.

---

# 17. Output Format

{
  "primary_strategy": "Trend Following",
  "alternative_strategies": [
    "Pullback",
    "Breakout"
  ],
  "strategy_score": 94,
  "recommended_timeframe": "H1",
  "warnings": [
    "Upcoming high-impact news in 2 hours"
  ]
}

---

# 18. AI Integration

The AI Reasoning Engine must explain:

Why this strategy was selected

Why other strategies were rejected

How the market regime influenced the decision

---

# 19. Logging

Store

Selected Strategy

Rejected Strategies

Score

Execution Time

Version

---

# 20. Testing

Validate

Strategy Matching

Scoring

Ranking

Market Compatibility

Risk Validation

Coverage Goal

95%

---

# 21. Future Enhancements

AI Strategy Optimization

Automatic Strategy Rotation

Historical Strategy Ranking

User-Created Strategies

Marketplace for Community Strategies

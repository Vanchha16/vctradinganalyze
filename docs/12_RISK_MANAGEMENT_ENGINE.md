# Risk Management Engine

Version: 1.1

Implementation (Phase 5C): docs/48_RISK_MANAGEMENT_ARCHITECTURE.md, ADR-062 through ADR-068.

---

# 1. Objective

The Risk Management Engine evaluates whether a potential trading setup is safe enough to recommend.

**Implementation note (Phase 5C, ADR-062):** "signal" here refers to a caller-supplied candidate trade setup (asset, timeframe, direction, entry/stop/target prices), passed directly in the API request - not a persisted `Signal` entity. No Signal Engine exists yet (docs/03 §11's `signals` table is Phase 6/7); this engine evaluates whatever specific setup it's asked about.

It does NOT generate BUY or SELL signals.

Its responsibility is to:

- Detect dangerous market conditions
- Reject low-quality setups
- Score trade quality
- Protect users from unnecessary risk
- Provide structured risk evidence

---

# 2. Responsibilities

The engine shall:

✔ Analyze volatility

✔ Analyze spread

✔ Detect high-impact news windows

✔ Analyze liquidity

✔ Detect session quality

✔ Analyze market correlation

✔ Validate Risk/Reward

✔ Calculate Trade Quality Score

✔ Approve or Reject setup

---

# 3. Input

Asset

Current Price

Spread

ATR

Volatility

Session

Economic Events

Technical Score

SMC Score

News Score

Confidence Score

---

# 4. Risk Factors

Market Volatility

Spread

Upcoming News

Trend Strength

Liquidity

Correlation

Session

Risk/Reward

Stop Loss Size

Confidence

---

# 5. Market Sessions

Asian

London

New York

Sydney

Overlap Sessions

London + New York

Highest Priority

---

# 6. Volatility Filter

Very Low

Low

Normal

High

Extreme

Rules

Extreme volatility

↓

Reject signal

Very Low volatility

↓

Reduce confidence

---

# 7. Spread Filter

**Implementation note (Phase 5C, ADR-065):** no spread data source exists anywhere in this project (see docs/03 §5's `CandleResponse` docstring). `spread` is an optional field on the evaluation request - supplied by the caller if it has a live quote. This filter is skipped (never defaulted/fabricated) when omitted.

Spread

Excellent

Acceptable

High

Extreme

Rules

High spread

↓

Reduce score

Extreme spread

↓

Reject signal

---

# 8. Economic Event Filter

Critical Event

Less than 30 minutes

↓

Reject

High Impact Event

Less than 60 minutes

↓

Reduce confidence

Medium Event

↓

Minor reduction

---

# 9. Correlation Filter

Avoid multiple highly correlated signals.

Examples

EURUSD + GBPUSD

XAUUSD + Silver

BTC + ETH

If correlation > 0.85

↓

Reduce quality score

---

# 10. Liquidity Filter

Detect

Low Liquidity

Normal

High

Excellent

Reject trading during

Holiday Sessions

Market Close

Abnormal Conditions

---

# 11. Trend Quality

Very Weak

Weak

Healthy

Strong

Very Strong

Weak trends reduce score.

---

# 12. Risk/Reward Validation

Minimum RR

1:2

Preferred

1:3

Excellent

1:4+

Reject setups below minimum threshold.

---

# 13. Stop Loss Validation

Check

Distance

ATR Ratio

Swing Structure

Liquidity Zone

Order Block

Reject unrealistic stop losses.

---

# 14. Position Sizing Guidance

The engine does NOT calculate account-specific lot sizes.

Instead it provides guidance:

Very Conservative

Conservative

Normal

Aggressive (high confidence only)

---

# 15. Trade Quality Score

Maximum

100

Components

Trend Quality

20

Technical

20

SMC

20

Risk

20

News

10

Economic

10

---

# 16. Decision Matrix

Trade Quality

90+

Excellent

80–89

Very Good

70–79

Good

60–69

Average

Below 60

Reject

---

# 17. Output

{
  "approved": true,
  "risk_level": "Medium",
  "trade_quality": 88,
  "risk_reward": "1:3",
  "warnings": [
    "High Impact News in 90 minutes"
  ],
  "position_guidance": "Conservative"
}

---

# 18. Logging

Store

Trade Quality

Risk Level

Warnings

Rejected Reason

Execution Time

---

# 19. Unit Testing

Volatility Filter

Spread Filter

News Filter

Correlation Filter

Liquidity Filter

RR Validation

Trade Quality

Coverage Goal

95%

---

# 20. Future Enhancements

Portfolio Risk

Maximum Daily Exposure

Maximum Weekly Exposure

Dynamic Correlation Model

Monte Carlo Risk Simulation

AI Risk Calibration
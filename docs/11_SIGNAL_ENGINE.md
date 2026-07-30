# Signal Engine

Version: 1.0

---

# 1. Objective

The Signal Engine is responsible for generating the final trading recommendation.

It does NOT calculate indicators.

It does NOT detect SMC.

It does NOT analyze news.

Its responsibility is to:

- Collect evidence
- Evaluate evidence
- Calculate confidence
- Assess risk
- Produce the final recommendation
- Generate an explainable report

---

# 2. Responsibilities

The engine shall:

✔ Receive evidence

✔ Validate evidence

✔ Remove conflicting evidence

✔ Calculate confidence

✔ Calculate risk

✔ Generate Entry

✔ Generate Stop Loss

✔ Generate Take Profit

✔ Calculate Risk/Reward

✔ Generate AI explanation

✔ Save signal

✔ Notify downstream services

---

# 3. Input

Technical Evidence

SMC Evidence

News Evidence

Economic Evidence

Risk Evidence

Market Data

Current Price

Timeframe

Asset

---

# 4. Evidence Model

Each engine submits evidence.

Example

{
    "source":"Technical",
    "title":"EMA Bullish Cross",
    "score":15,
    "direction":"BUY"
}

---

# 5. Weight Distribution

Technical Analysis

35%

SMC

30%

Economic Events

15%

News Sentiment

10%

Risk Engine

10%

Total

100%

---

# 6. Recommendation Rules

BUY

Evidence strongly bullish.

SELL

Evidence strongly bearish.

WAIT

Mixed evidence

Low confidence

High risk

High volatility

Missing confirmation

---

# 7. Confidence Score

Range

0–100

Confidence Levels

95–100

Extremely High

85–94

Very High

75–84

High

60–74

Medium

Below 60

Low

---

# 8. Risk Assessment

Risk Levels

Very Low

Low

Medium

High

Extreme

Factors

ATR

Spread

Volatility

Upcoming News

Liquidity

Trend Strength

Correlation

---

# 9. Entry Generation

Determine:

Entry Price

Market Order

Limit Order

Stop Order

Reasons

Current Structure

Order Block

Support

Resistance

Liquidity

---

# 10. Stop Loss

Calculate using

ATR

Swing Low

Swing High

Order Block

Volatility

Minimum RR

Store

Distance

Percentage

Price

---

# 11. Take Profit

Calculate using

Resistance

Support

Liquidity

FVG

ATR

Trend

Store

TP1

TP2

TP3

---

# 12. Risk Reward

Minimum

1 : 2

Preferred

1 : 3

Excellent

1 : 4+

Reject setups below minimum unless manually approved by future admin rules.

---

# 13. Conflict Resolution

Example

Technical

BUY

SMC

SELL

News

BUY

Economic

SELL

Risk

HIGH

Result

WAIT

Reason

Conflicting evidence.

---

# 14. AI Explanation

Every signal must explain

Trend

Momentum

Market Structure

SMC

News

Economic Events

Risk

Confidence

---

# 15. Evidence Report

Example

BUY EURUSD

Confidence

91%

Evidence

✓ Daily Trend Bullish

✓ H4 Bullish BOS

✓ Fresh Order Block

✓ Bullish FVG

✓ CPI Better Than Forecast

✓ RSI Momentum Strong

Warnings

High Impact News in 2 Hours

Risk

Medium

---

# 16. Output Format

{
    "asset":"EURUSD",
    "timeframe":"H1",
    "recommendation":"BUY",
    "confidence":91,
    "risk":"Medium",
    "entry":1.18600,
    "stop_loss":1.18200,
    "take_profit":[
        1.19000,
        1.19400,
        1.19800
    ],
    "risk_reward":"1:3",
    "reasoning":[]
}

---

# 17. Signal Lifecycle

Receive Evidence

↓

Validate

↓

Weight Scores

↓

Resolve Conflicts

↓

Risk Assessment

↓

Generate Recommendation

↓

Generate AI Explanation

↓

Store Signal

↓

Notify Dashboard

↓

Send Telegram

---

# 18. Signal Status

Draft

Active

Triggered

Expired

Cancelled

Closed

Successful

Stopped Out

---

# 19. Logging

Store

Confidence

Evidence

Execution Time

Recommendation

Risk

Warnings

Model Version

---

# 20. Performance

Signal Generation

<2 seconds

Confidence Calculation

<100ms

Risk Assessment

<200ms

---

# 21. Testing

Weighting

Risk

Conflict Resolution

Confidence

TP

SL

RR

Evidence Validation

Coverage Goal

95%

---

# 22. Future Enhancements

Machine Learning Confidence Calibration

Adaptive Risk Engine

Portfolio-Level Signals

Cross-Asset Confirmation

Personalized Signal Profiles
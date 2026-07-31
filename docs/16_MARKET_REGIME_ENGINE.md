# Market Regime Engine

Version: 1.0

Status: Implemented in Phase 4C. See docs/44_MARKET_REGIME_ARCHITECTURE.md for the concrete algorithms, classification precedence rule, and API contract. §16 ("Strategy Compatibility") and §17 ("AI Integration") are documentation guidance for future engines (Signal Engine/AI Orchestrator, Phase 6) - never this engine's output (ADR-043). §2's "Detect exhaustion" has no dedicated analyzer; it's folded into Pullback/Reversal evidence as a warning (docs/44 §9). §3's "Uncertain" is the fallback when no other regime's criteria are met with sufficient confidence, never a positively-detected condition (docs/44 §10).

---

# 1. Objective

The Market Regime Engine identifies the current market environment.

It does NOT generate BUY or SELL recommendations.

Its purpose is to classify market conditions so that every downstream engine can adapt its behavior accordingly.

---

# 2. Responsibilities

The engine shall:

- Detect market regime
- Measure trend strength
- Detect volatility regime
- Detect consolidation
- Detect breakouts
- Detect exhaustion
- Publish regime evidence

---

# 3. Supported Market Regimes

Trending Bullish

Trending Bearish

Ranging

Accumulation

Distribution

Breakout

Pullback

Reversal

High Volatility

Low Volatility

Uncertain

---

# 4. Inputs

Price Candles

Volume

ATR

ADX

EMA

VWAP

Support

Resistance

SMC Events

Economic Risk

---

# 5. Regime Detection Pipeline

Collect Data

↓

Calculate Indicators

↓

Analyze Trend

↓

Analyze Volatility

↓

Analyze Structure

↓

Detect Regime

↓

Assign Confidence

↓

Publish Evidence

---

# 6. Trend Detection

Bullish Trend

Requirements

Higher Highs

Higher Lows

EMA Alignment

ADX Above Threshold

Bearish Trend

Requirements

Lower Highs

Lower Lows

EMA Alignment

ADX Above Threshold

---

# 7. Range Detection

Characteristics

Flat EMA

Weak ADX

Price Between Support & Resistance

Low Momentum

Output

Range Width

Range Strength

---

# 8. Breakout Detection

Requirements

Break of Key Level

Volume Confirmation

Momentum Increase

Close Beyond Resistance or Support

Confirmation Candle

Output

Bullish Breakout

Bearish Breakout

False Breakout

---

# 9. Accumulation

Characteristics

Sideways Movement

Increasing Volume

Stable Volatility

Institutional Buying Evidence

Output

Accumulation Score

---

# 10. Distribution

Characteristics

Sideways Movement

Selling Pressure

Weak Momentum

Institutional Selling Evidence

Output

Distribution Score

---

# 11. Pullback Detection

Requirements

Trend Still Valid

Temporary Counter-Trend Move

Support Holds

Momentum Weakens

Output

Healthy Pullback

Deep Pullback

Potential Reversal

---

# 12. Reversal Detection

Signals

CHOCH

Strong BOS

Momentum Shift

Volume Confirmation

Output

Bullish Reversal

Bearish Reversal

Reversal Confidence

---

# 13. Volatility Regime

Very Low

Low

Normal

High

Extreme

Measurements

ATR

Historical Volatility

Range Expansion

Volume

---

# 14. Regime Confidence

95-100

Extremely Reliable

85-94

Very Reliable

75-84

Reliable

60-74

Moderate

Below 60

Uncertain

---

# 15. Engine Output

{
    "regime": "Trending Bullish",
    "confidence": 91,
    "trend_strength": "Strong",
    "volatility": "Normal",
    "breakout": false,
    "accumulation": false,
    "distribution": false,
    "warnings": [
        "Resistance within 30 pips"
    ]
}

---

# 16. Strategy Compatibility

Trending Bullish

Recommended

Trend Following

Breakout Trading

Pullback Entries

---

Ranging

Recommended

Mean Reversion

Range Trading

Support & Resistance

---

High Volatility

Recommended

Reduced Position Size

Higher Stop Loss

Wait for Confirmation

---

Low Volatility

Recommended

Avoid Breakout Entries

Monitor for Expansion

---

# 17. AI Integration

The AI Reasoning Engine must include the current market regime in every explanation.

Example

"The market is currently in a strong bullish trend with healthy volatility, making continuation setups more reliable."

---

# 18. Logging

Store

Detected Regime

Confidence

Trend Strength

Volatility

Execution Time

Version

---

# 19. Testing

Validate

Trend Detection

Range Detection

Breakout Detection

Pullback Detection

Reversal Detection

Volatility Classification

Coverage Goal

95%

---

# 20. Future Enhancements

Hidden Markov Models (HMM)

Machine Learning Regime Detection

Adaptive Strategy Selection

Regime Transition Prediction

Cross-Asset Regime Analysis
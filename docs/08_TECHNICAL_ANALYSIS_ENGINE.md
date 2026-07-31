# Technical Analysis Engine

Version: 1.0

---

# 1. Objective

The Technical Analysis Engine is responsible for transforming raw market data into structured technical insights.

It DOES NOT generate BUY or SELL signals.

Its purpose is to provide objective technical evidence to the AI Orchestrator.

---

# 2. Responsibilities

The engine shall:

- Calculate indicators
- Detect trends
- Detect momentum
- Detect volatility
- Detect support/resistance
- Analyze multiple timeframes
- Generate a technical score
- Return structured results

---

# 3. Input

Required Input

Asset

Timeframe

OHLCV Candles

Spread

Volume

Current Price

---

# 4. Supported Timeframes

M1

M5

M15

M30

H1

H4

D1

W1

MN

---

# 5. Indicators

Trend

EMA 20

EMA 50

EMA 100

EMA 200

SMA 200

---

Momentum

RSI (14)

MACD

Stochastic RSI

CCI

Momentum

---

Volatility

ATR

Bollinger Bands

Standard Deviation

---

Volume

VWAP

OBV

Volume Moving Average

Relative Volume

---

Trend Strength

ADX

DI+

DI-

---

# 6. Support & Resistance

Detect

Swing Highs

Swing Lows

Daily High

Daily Low

Weekly High

Weekly Low

Monthly High

Monthly Low

Round Numbers

Psychological Levels

---

# 7. Trend Detection

Bullish

Bearish

Sideways

Trend Strength

Weak

Moderate

Strong

Very Strong

---

# 8. Multi-Timeframe Analysis

Priority

Daily

↓

H4

↓

H1

↓

M15

Rules

Higher timeframe always has greater weight.

Example

Daily Bullish

H4 Bullish

H1 Pullback

M15 Bullish

Result

Bullish Continuation

---

# 9. Indicator Agreement

Each indicator contributes to a technical score.

**Note (Phase 4A): the example below is illustrative only and does not sum to the stated maximum of 100 (20+15+15+10+10+5 = 75).** The definitive, complete scoring formula actually implemented (a 100-point breakdown across trend/strength/momentum/oscillator/volume/volatility/support-resistance, with per-conflict penalties) is documented in `docs/42_TECHNICAL_ANALYSIS_ARCHITECTURE.md` §7 and **ADR-028** - treat that as canonical, not the example below.

Example (illustrative, superseded by ADR-028 - see above)

EMA Alignment

+20

MACD Bullish

+15

ADX Strong

+15

RSI Healthy

+10

VWAP Above Price

+10

ATR Stable

+5

Maximum Technical Score

100

---

# 10. Conflict Detection

Example

EMA Bullish

MACD Bearish

ADX Weak

Result

Mixed Trend

Reduce confidence

**Note (Phase 4A):** implemented as a fixed per-conflict score penalty (docs/42 §8, ADR-028), not a trend-verdict override - the trend classification itself is decided solely by moving-average alignment (docs/42 §9); conflicts affect `technical_score` only.

---

# 11. Output Format

{
    "trend": "Bullish",
    "strength": "Strong",
    "technical_score": 82,
    "score_breakdown": {
        "trend": 25.0,
        "momentum": 15.0,
        "oscillator": 15.0,
        "volume": 15.0,
        "volatility": 10.0,
        "support_resistance": 5.0,
        "penalties": -3.0,
        "total": 82.0
    },
    "support": {"price": 1.18400, "source": "swing_low", "strength": "weak"},
    "resistance": {"price": 1.19150, "source": "daily_high", "strength": "moderate"},
    "indicators": {
        "ema20": "...",
        "ema50": "...",
        "rsi": 58,
        "macd": "Bullish",
        "adx": 32
    },
    "warnings": []
}

**Note (Phase 4A):** `score_breakdown` (explainable per-factor components) and structured `support`/`resistance` objects (price + source + strength, not bare numbers) were added per Phase 4A's approved refinements - see docs/42 and `app/schemas/technical_analysis.py` for the exact shape.

---

# 12. Validation Rules

Reject analysis if:

Missing candles

Corrupted OHLC data

Invalid timeframe

Negative prices

Missing volume (where required)

---

# 13. Performance

Indicator calculation

<100ms

Multi-timeframe analysis

<500ms

Memory efficient

Vectorized calculations preferred

---

# 14. Logging

Log:

Calculation duration

Indicator values

Warnings

Errors

Asset

Timeframe

---

# 15. Unit Testing

Each indicator must have independent tests.

EMA

RSI

MACD

ATR

ADX

VWAP

OBV

Support/Resistance

Trend Detection

Coverage Target

95%

---

# 16. Future Enhancements

Market Regime Detection

Machine Learning Trend Classifier

Adaptive Indicators

Custom Indicator Plugins

Institutional Volume Models
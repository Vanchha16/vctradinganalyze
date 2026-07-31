# Smart Money Concepts (SMC) Engine

Version: 1.0

Status: Implemented in Phase 4B. See docs/43_SMC_ARCHITECTURE.md for the concrete algorithms, data model, lifecycle states, and API contract. Concepts referenced during Phase 4B planning that do **not** appear in this document - Inverse Fair Value Gaps (IFVG), an Internal/External BOS distinction, a dedicated Displacement concept, and Market Imbalance - were deliberately excluded from implementation per "never invent architecture" (docs/43 §9, §18).

---

# 1. Objective

The Smart Money Concepts (SMC) Engine identifies institutional market structure and liquidity behavior.

The engine DOES NOT generate BUY or SELL recommendations.

Its responsibility is to detect professional trading concepts and provide structured evidence to the AI Orchestrator.

---

# 2. Responsibilities

The engine shall:

- Detect market structure
- Detect liquidity zones
- Detect Order Blocks
- Detect Fair Value Gaps
- Detect Break of Structure
- Detect Change of Character
- Detect Premium & Discount Zones
- Detect Mitigation Blocks
- Detect Breaker Blocks
- Calculate SMC score
- Return structured analysis

---

# 3. Required Input

Asset

Timeframe

OHLCV Candles

Swing Highs

Swing Lows

Current Price

Volume

Trend Direction

---

# 4. Supported Timeframes

M1

M5

M15

M30

H1

H4

Daily

Weekly

Monthly

---

# 5. Market Structure

Detect

Higher High (HH)

Higher Low (HL)

Lower High (LH)

Lower Low (LL)

Result

Bullish Structure

Bearish Structure

Range

Transition

---

# 6. Break of Structure (BOS)

Bullish BOS

Price closes above previous significant swing high.

Bearish BOS

Price closes below previous significant swing low.

Store

Direction

Strength

Break Price

Break Time

Confirmation Status

---

# 7. Change of Character (CHOCH)

Detect the first meaningful shift in market direction.

Store

Previous Trend

New Trend

Confidence

Confirmation Candle

---

# 8. Order Blocks

Detect

Bullish Order Block

Bearish Order Block

Store

Zone High

Zone Low

Mitigated

Touched

Broken

Strength Score

Freshness Score

Volume Confirmation

---

# 9. Fair Value Gaps (FVG)

Detect

Bullish FVG

Bearish FVG

Store

Gap High

Gap Low

Filled

Partially Filled

Open

Gap Size

Priority

---

# 10. Liquidity

Detect

Buy Side Liquidity

Sell Side Liquidity

Equal Highs

Equal Lows

Liquidity Sweep

False Breakout

Store

Liquidity Level

Sweep Time

Direction

Volume

---

# 11. Premium & Discount Zones

Based on current dealing range.

Return

Premium

Equilibrium

Discount

Current Position

Distance

---

# 12. Mitigation Blocks

Detect

Fresh

Mitigated

Invalidated

Store

Zone

Touch Count

Reaction Strength

---

# 13. Breaker Blocks

Detect

Bullish Breaker

Bearish Breaker

Store

Strength

Confirmation

Retest

---

# 14. Confluence Detection

Examples

Bullish BOS

+

Bullish Order Block

+

Discount Zone

+

Liquidity Sweep

=

High Confluence

Return

Confluence Score

Maximum

100

---

# 15. Multi-Timeframe Analysis

Priority

Weekly

↓

Daily

↓

H4

↓

H1

↓

M15

Lower timeframes must align with higher timeframe bias whenever possible.

---

# 16. Conflict Detection

Example

Daily Bullish

H1 Bearish

Return

Pullback

Do not classify as full bearish reversal without confirmation.

---

# 17. Output Format

**Corrected in Phase 4B (docs/43 §6)**: the flat example below is superseded - `bos`/`choch` are lists of records (per §6/§7's own field descriptions), not booleans, and `smc_score` is one component of an explainable `score_breakdown` (ADR-036), not a single opaque number. `app/schemas/smc.py` is the canonical shape.

{
    "market_structure": "Bullish",
    "bos": true,
    "choch": false,
    "order_blocks": [
        {
            "type": "Bullish",
            "high": 1.1860,
            "low": 1.1845,
            "strength": 92
        }
    ],
    "fvg": [
        {
            "direction": "Bullish",
            "status": "Open"
        }
    ],
    "liquidity": {
        "buy_side": true,
        "sell_side": false
    },
    "premium_discount": "Discount",
    "smc_score": 87
}

---

# 18. Validation Rules

Reject analysis when

Insufficient candles

Invalid swing structure

Corrupted OHLC data

Missing timeframe

---

# 19. Performance

Single timeframe

<100ms

Multi-timeframe

<500ms

Memory efficient

Vectorized calculations preferred

---

# 20. Logging

Store

Execution time

Detected events

Scores

Warnings

Errors

---

# 21. Unit Testing

Every detector requires isolated tests.

BOS

CHOCH

Order Blocks

FVG

Liquidity

Mitigation

Breaker

Premium / Discount

Confluence

Coverage Target

95%

---

# 22. Future Enhancements

Machine Learning SMC Validation

Institutional Flow Detection

Volume Profile Integration

Market Auction Theory

ICT Session Analysis

Liquidity Heatmaps
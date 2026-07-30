# News Sentiment Engine

Version: 1.0

---

# 1. Objective

The News Sentiment Engine collects, filters, analyzes, and scores financial news that may affect the market.

It does NOT generate BUY or SELL recommendations.

It provides structured sentiment evidence to the AI Orchestrator.

---

# 2. Responsibilities

The engine shall:

- Collect news
- Remove duplicates
- Classify importance
- Detect affected assets
- Analyze sentiment
- Detect breaking news
- Generate AI summaries
- Score market impact
- Publish evidence

---

# 3. Supported Sources

Tier 1

Reuters

Bloomberg

Associated Press

Central Bank Statements

Official Government Releases

---

Tier 2

Forex Factory

Investing.com

Trading Economics

CoinDesk

CoinTelegraph

---

Tier 3

X (Twitter) Verified Accounts

Federal Reserve

ECB

BOE

BOJ

BLS

IMF

World Bank

---

# 4. News Pipeline

Fetch News

↓

Normalize Format

↓

Remove Duplicates

↓

Detect Language

↓

Translate (if needed)

↓

Classify Category

↓

Extract Assets

↓

Sentiment Analysis

↓

Importance Score

↓

AI Summary

↓

Store

↓

Publish Evidence

---

# 5. Categories

Central Bank

Inflation

Employment

GDP

Interest Rates

Politics

War

Energy

Commodities

Crypto

Regulation

Corporate Earnings

Breaking News

---

# 6. Supported Assets

Forex

Gold

Silver

Oil

Crypto

Indices

Stocks (Future)

---

# 7. Sentiment

Values

Very Bullish

Bullish

Neutral

Bearish

Very Bearish

Each sentiment includes

Confidence

Reason

Affected Assets

---

# 8. Importance Levels

Critical

High

Medium

Low

Ignore

Examples

FOMC

Critical

CPI

Critical

Fed Speech

High

Company Earnings

Medium

Minor Political News

Low

---

# 9. AI Summary

Maximum

150 words

Must include

Summary

Market Impact

Affected Assets

Risk

Confidence

---

# 10. Duplicate Detection

Duplicate when

Same URL

Same Headline

Same Event

Same AI Hash

Keep only highest-quality source.

---

# 11. Breaking News

Examples

Emergency Fed Meeting

Bank Collapse

War

Unexpected Rate Decision

Flash Crash

Major Exchange Outage

Priority

Immediate Processing

---

# 12. Output Format

{
    "headline": "...",
    "category": "Inflation",
    "importance": "Critical",
    "sentiment": "Bullish USD",
    "confidence": 91,
    "affected_assets": [
        "EURUSD",
        "XAUUSD"
    ],
    "summary": "...",
    "published_at": "...",
    "source": "Reuters"
}

---

# 13. Evidence Output

Each processed article produces evidence.

Example

Source:
News Engine

Evidence

USD Bullish

Score

18

Reason

CPI above expectations

---

# 14. AI Guardrails

AI must never

Invent news

Invent quotes

Invent numbers

Invent forecasts

Every statement must reference the original article.

---

# 15. Performance

Breaking News

<30 seconds

Normal News

<2 minutes

Sentiment

<5 seconds

---

# 16. Logging

Store

Source

Execution Time

Sentiment

Confidence

Errors

Duplicate Status

---

# 17. Unit Testing

Duplicate Detection

Sentiment

Asset Detection

Importance

AI Summary

Translation

Coverage Goal

95%

---

# 18. Future Enhancements

FinBERT

Multi-language Support

Event Clustering

Rumor Detection

Social Sentiment

Market Reaction Prediction
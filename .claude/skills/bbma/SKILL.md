---
name: bbma
description: BBMA (Bollinger Bands + Moving Average) trading strategy rules - Extreme, MHV, Re-entry, Candle Arah, CSM/CSAK/CSK, ZZL, the cycle order, and the TF1/TF2/TF3 multi-timeframe codes. Use when reading, analysing, specifying or implementing BBMA setups in this project, when a chart or signal is described in BBMA terms (Extreme, MHV, re-entry, TP Wajib, CSAK, candle arah), or when deciding how a deterministic signal engine should identify entries. Full reference is docs/61_BBMA_STRATEGY_REFERENCE.md.
---

# BBMA

A deterministic, rule-based strategy by Oma Ally (Malaysia, ~2007). Every
term is defined by where price and moving averages sit relative to
Bollinger Bands — which is the point: unlike `AIOrchestratorEngine`, BBMA
has a portable formula and can be implemented, tested and reproduced
without an LLM call.

**Full detail, including source provenance and every gap in the source
material, is in `docs/61_BBMA_STRATEGY_REFERENCE.md`. Read it before
writing any BBMA implementation.** This file is the working summary.

## Indicators (exact settings matter)

| Line | Type | Period | Apply to |
|---|---|---|---|
| Top / Mid / Low BB | Bollinger Bands, dev 2, shift 0 | 20 | Close |
| EMA 50 | Exponential | 50 | Close |
| MA5H | Linear Weighted | 5 | High |
| MA10H | Linear Weighted | 10 | High |
| MA5L | Linear Weighted | 5 | Low |
| MA10L | Linear Weighted | 10 | Low (see Open Questions) |

Mid BB **is** SMA(20). "MA5/10 High" and "MA5/10 Low" are *bands* — the
pair of lines together, not one line.

## The two basic laws

1. **An MA may not be outside the BB.** MA5 outside → **Extreme**.
   (MA10 also outside → *Extreme Magic*, stronger reversal.)
2. **A candle may not close outside the BB.** When it does:
   - BB expanding/vertical → **Momentum** (continuation)
   - BB flat/horizontal → **reversal** (price returns, at least to Mid BB)

Entry-side law: **buy only at MA5/10 Low, sell only at MA5/10 High.**

## The cycle — apply in this order, never invent a step

```
Extreme → TP Wajib → MHV → Candle Arah → Re-entry → Momentum → Re-entry → …
```

The same pattern replays on smaller timeframes inside each leg of a
larger one (the manual's "forex mainframe").

## Setups

**Extreme** — the early warning that a move is ending. A *signal*, not
yet a setup.
- SELL: MA5H leaves the **Top** BB · BUY: MA5L leaves the **Low** BB
- Needs all three: MA5 leaves BB → **CS Reverse** (stops the move; mark
  its body, it is the highest-volume candle) → **CS Retest** (the entry)
- **TP is mandatory** at MA5/MA10, at most Mid BB. No compromise.
- An Extreme *against* the trend major (EMA50) is a **weak** Extreme.

**MHV** (Market Hilang Volume — market *loses* volume) — double top /
bottom, always **after** an Extreme.
- Candle **fails** to close outside Top/Low BB (a wick may exceed; the
  close may not)
- CS Reverse that does **not** pass MA5/10 or Mid BB
- CS Retest = entry
- **Cancelled** the moment a candle does close outside the band
- TP at Low BB (sell) / Top BB (buy) — negotiable, unlike Extreme's

**Candle Arah** (direction candle, appears after MHV)
- *kukuh* (strong): closes past MA5/10 **and** Mid BB
- *tak kukuh* (weak): closes past MA5/10 only

**Re-entry — the primary entry.** "The best entry, because of the
confirmation at strong direction."
- At MA5/MA10 — Low band to buy, High band to sell
- The candle **must not close past** MA5/10 (that would be CSK)
- Strongest at the MA5 + MA10 + Mid BB confluence (add EMA50 → "no compromise")
- **Every direction or momentum must be followed by a re-entry**
- Sideways *creates* re-entry
- **Never enter on the first candle** — wait for it to close confirming, enter on the second
- At a confluence expect **minimum 3 candles** of movement on that timeframe

**CSM** (momentum) — closes outside Top BB (buy) / Low BB (sell). Then
wait for the pullback to Re-entry.
- Direction → Re-entry → **no** momentum ⇒ close, market reverses
- Direction → **no** Re-entry ⇒ may hold and wait for one

**CSAK/CSD** — any candle **breaking Mid BB**. Closes above → CSAK Buy,
buy at MA5/10 Low above Mid BB. Closes below → CSAK Sell, sell at MA5/10
High below Mid BB.

**CSK** — a candle breaking outside MA5/10 High/Low.

**ZZL** (Zone Zero Loss) — all MAs above Mid BB **and** Mid BB above
EMA50 (bullish; invert for bearish).

## Trend major (EMA50)

Above → buy bias, below → sell bias, flat → no flow. Works properly from
**D1 minimum**; H4 does not carry trend major. If D1 says buy and H4 says
sell, **follow D1**.

## Multi-timeframe: TF1 direction → TF2 setup → TF3 entry

| Style | TF1 | TF2 | TF3 |
|---|---|---|---|
| Swing / Position | MN | W1 | D1 |
| Intraday | H4 | H1 | M15 |
| Scalping | H1 | M15 | M5 |
| Extreme Scalping | M15 | M5 | M1 |

Code table (R=Re-entry, E=Extreme, M=MHV, EE=double Extreme):

```
TF1   R   R   R   R
TF2   E   R   E   M
TF3   M   E   E   EE
```

Named setups: **RRE**, **REE**, **REM**, **Conservative** (R → reject
EMA50 → R), **Diamond** (ZZL → reject EMA50 → R), **Full Setup** (1 TF),
**RZZL**.

## Exits

Hold/add on `CSAK >> Re-entry` and `CSM >> Re-entry`. Exit when **any** of:
MA5/10 cross over · MA5/10 leave Low/Top BB with a reverse candle closing ·
TF1's own target reached (its Re-entry, or Top/Low BB).

## Open questions — do NOT silently invent answers to these

This project's rules forbid inventing architecture, and these gaps are in
the *source material*, not in our understanding of it. Each needs an
operator decision plus an ADR before it can be coded.

1. **`CS Reverse` and `CS Retest` have no numeric definition anywhere** —
   prose only ("a candle that stops the move"). They are central to both
   Extreme and MHV. No body ratio, wick tolerance or lookback is given.
   **This is the blocker everything else waits on.**
2. **Extreme is defined two incompatible ways** — the English manual says
   *MA5 leaves the BB* (mechanical, codeable); the Khmer deck says *3
   candles break → reverse → retest* (not reproducible as written).
3. **MA10L conflicts** — both Khmer decks say "apply to **High**", the
   English manual says **Low**. That line is the buy entry band.
4. **"Volume" has no usable source** — MHV and CS Reverse key off the
   "highest volume" candle, but `price_candles.volume` for spot XAUUSD is
   broker tick-volume with per-provider meaning.

## Project context before implementing

- **Nothing is implemented.** No ADR, no code, no engine.
- BB and EMA already exist in `technical_analysis/`; the four
  **linear-weighted High/Low MAs do not**.
- BBMA would be the "second, independent recommendation source" ADR-085
  explicitly left the door open for — it does not replace
  `AIOrchestratorEngine` without its own ADR.
- Its rule-defined entry bands would also address ADR-145's root cause.
- BBMA reads **three timeframes at once**; at the current one-active-symbol
  quota ceiling (ADR-140) that is feasible for one symbol only.
- **No backtesting exists** in this project, and the source material gives
  no win rate, sample size or drawdown — the webinar leaves validation to
  the reader. Do not present BBMA as validated.

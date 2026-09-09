# BBMA Strategy Reference

Version: 1.0
Status: **Reference only — nothing here is implemented.**

Source material supplied by the operator (2026-09-09):

- `BBMA Trading Strategy .pdf` — the original BBMA technique manual (English,
  translated from Malay; the most precise of the four)
- `BBMA + Advance model.pdf` / `BBMA Teaching Webinar.pdf` — Khmer training
  decks by Keo Pidor, approved by TRADER007KH
- `SIGNALS AND SETUP.pdf` — the seven named multi-timeframe setups

BBMA ("Bollinger Bands + Moving Average") was created by **Oma Ally**
(Malaysia, ~2007, published ~2010). It is a **deterministic, rule-based**
system: every term below is defined by the position of price and moving
averages relative to Bollinger Bands. That is the important property for
this project — unlike `AIOrchestratorEngine`, it has a portable formula.

---

# 1. Indicator Set

All are standard MT4/MT5 indicators. Exact settings matter.

| Name | Type | Period | Apply to | Notes |
|---|---|---|---|---|
| Top BB / Mid BB / Low BB | Bollinger Bands | 20 | Close | Deviation 2, shift 0. **Mid BB = SMA(20)** |
| EMA 50 | Exponential MA | 50 | Close | "Trend major" |
| MA5H | Linear Weighted MA | 5 | **High** | |
| MA10H | Linear Weighted MA | 10 | **High** | |
| MA5L | Linear Weighted MA | 5 | **Low** | |
| MA10L | Linear Weighted MA | 10 | **Low** | See discrepancy §7.1 |

"MA5/10 High" and "MA5/10 Low" are used throughout as *bands* — the pair
of lines, not one line. Entries happen **at** those bands.

---

# 2. The Two Basic Laws

Everything in BBMA derives from two rules and their violations:

1. **A moving average may not be outside the Bollinger Band.**
   When MA5 leaves the BB → **Extreme**.
   (When MA10 also leaves → *Extreme Magic*, a stronger reversal signal.)

2. **A candle may not close outside the Bollinger Band.**
   When it does, the meaning depends on BB shape:
   - BB **expanding / vertical** → **Momentum** (continuation)
   - BB **flat / horizontal** → **reversal** (price returns, at least to Mid BB)

Entry-side rule (§3 of the manual's Basic Law):

> **Buy only at MA5/10 Low. Sell only at MA5/10 High.**

## 2.1 Mid BB

> *"As long as none of the candle passes the Mid BB, there won't be any
> movement to the new direction."* — Oma Ally

Mid BB is the divider between the buy zone (Mid→Top) and the sell zone
(Mid→Low), and doubles as the trend guide (pointing up / down / flat).

## 2.2 EMA 50 (trend major)

- Candles above EMA50 → uptrend bias (buy)
- Candles below EMA50 → downtrend bias (sell)
- Flat → sideways, no flow
- An Extreme *against* the trend major is a **weak Extreme**
- EMA50 works properly from **D1 minimum**; H4 does not carry trend major
- If D1 says buy and H4 says sell, **follow D1**

---

# 3. The Setups

## 3.1 Extreme

The early signal that a move is ending. **A signal, not yet a setup.**

Definition:
- **Extreme SELL** — MA5H (and price) leaves the **Top** BB
- **Extreme BUY** — MA5L (and price) leaves the **Low** BB

Validation sequence (all three required):
1. MA5 leaves the BB
2. **CS Reverse** — a candle that stops the move (this is the highest-volume
   candle; mark its body)
3. **CS Retest** — price returns to the marked level. **This is the entry.**

The Khmer deck states the same as: *3 candles break >> Reverse >> Retest.*

**TP is mandatory ("TP Wajib") at MA5/MA10, at most Mid BB — no compromise.**

## 3.2 TPW (TP Wajib)

The obligatory take-profit that follows every Extreme. Deck definition:
after the Extreme, price returns to touch Re-entry **without** breaking
Mid BB.

## 3.3 MHV — Market Hilang Volume (market *loses* volume)

Occurs **after** an Extreme. Known shape: double top / double bottom.

Validation (all required):
1. Candle **fails** to close outside Top/Low BB — a wick may exceed it, the
   close may not
2. **CS Reverse**, which does **not** pass MA5/10 or Mid BB
3. **CS Retest** — the entry
4. Must occur after an Extreme

**Cancelled** the moment price does close outside the Top/Low BB.

TP: Low BB (for a sell) / Top BB (for a buy) — the manual calls this
"negotiable", unlike Extreme's mandatory TP. If the next candle closes
*outside* the BB there is momentum: hold. If it closes *inside*: close.

## 3.4 Candle Arah (direction candle)

Appears after MHV. Two grades:

| Grade | Condition | Meaning |
|---|---|---|
| **CS arah kukuh** (strong) | closes past MA5/MA10 **and** past Mid BB | direction confirmed |
| **CS arah tak kukuh** (weak) | closes past MA5/MA10 only | not yet confirmed |

## 3.5 Re-entry — the primary entry

> *"Re entry is the best entry, because of the confirmation at strong direction."*

- Placed at **MA5/MA10** — Low band for buys, High band for sells
- The candle **must not close past** MA5/MA10 (that would be CSK, §3.7)
- **Strongest** at the confluence of MA5, MA10 and Mid BB (add MA50 → "no compromise")
- **Every direction or momentum must be followed by a re-entry**
- Sideways/ranging *creates* re-entry
- At a MA5/MA10/MidBB confluence, expect **minimum 3 candles** of movement on
  that timeframe (H1 → 3 hours; H4 → 12 hours) — during which smaller
  timeframes should give their own entries
- **Never enter on the first candle** — wait for it to confirm (close below
  MA5/MA10), enter on the second
- Do **not** enter near a CS Arah

## 3.6 Momentum / CSM

**CSM** = candle closing outside a band:
- **CSM Buy** — closes outside **Top** BB
- **CSM Sell** — closes outside **Low** BB

After a CSM, wait for the pullback to Re-entry; take the *first* level that
touches and closes Reject/bullish (buy) or Reject/bearish (sell), then look
for the next.

Sequence law: **Direction → Re-entry → Momentum → Re-entry → …**
- Direction, re-entry, **no** momentum → close; market will reverse
- Direction, **no** re-entry → allowed to hold and wait for one

## 3.7 CSAK / CSD and CSK

- **CSAK** — any candle that **breaks Mid BB**
  - closes **above** Mid BB → **CSAK Buy** → buy at MA5/10 **Low**, above Mid BB
  - closes **below** Mid BB → **CSAK Sell** → sell at MA5/10 **High**, below Mid BB
- **CSK** — a candle that breaks **outside MA5/10 High/Low**

## 3.8 ZZL (Zone Zero Loss)

From `SIGNALS AND SETUP.pdf`: **all MAs above Mid BB, and Mid BB above
EMA 50** (bullish case; invert for bearish).

---

# 4. The Cycle

The canonical order — the manual insists BBMA is applied **in this order**
and that you must never invent a setup out of sequence:

```
Extreme → TP Wajib → MHV → Candle Arah → Re-entry → Momentum → Re-entry → …
```

The manual calls the repetition the *"forex mainframe"* — the same pattern
replays on smaller timeframes inside each leg of a larger one.

---

# 5. Multi-Timeframe

Three timeframes are read together: **TF1 (direction) → TF2 (setup) →
TF3 (entry)**.

| Style | TF1 | TF2 | TF3 |
|---|---|---|---|
| Swing / Position | MN | W1 | D1 |
| Intraday | H4 | H1 | M15 |
| Scalping | H1 | M15 | M5 |
| Extreme Scalping | M15 | M5 | M1 |

The code table (R = Re-entry, E = Extreme, M = MHV, EE = double Extreme):

```
TF1   R   R   R   R
TF2   E   R   E   M
TF3   M   E   E   EE
```

## 5.1 The seven named setups

From `SIGNALS AND SETUP.pdf`:

1. **RRE** — Re-entry → Re-entry → Extreme
2. **REE** — Re-entry → Extreme → Extreme
3. **REM** — Re-entry → Extreme → MHV
4. **Conservative** — Re-entry → Reject EMA50 → Re-entry
5. **Diamond** — ZZL → Rejected EMA50 → Re-entry
6. **Full Setup** — single timeframe
7. **RZZL** — Re-entry + ZZL

## 5.2 Cheat-sheet rows

| # | TF1 | TF2 | TF3 |
|---|---|---|---|
| **#1** | Re-entry | Extreme (MA50 + MA5 H/L + top/low/mid BB) | MHV, MA5/10 cross, full structure |
| **#2** | NO CSM | Extreme at Top/Low (MA5 + BB) | MHV, MA5/10 cross |
| **#3** | MHV | Extreme at Top/Low (MA5 + BB) | MHV, MA5/10 cross |

## 5.3 TF promotion (when TF2 becomes TF1)

| TF1 shows | then TF2 gives |
|---|---|
| CSK breaks hard but not out of MA5/10 | Re-entry |
| Retest candle in progress | MHV → CSAK → Re-entry |
| Candle not breaking MA5/10 high/low | depends on Extreme NO CSM on TF2 |

---

# 6. Trade Management

## 6.1 Holding with the flow

Stay in / add: `CSAK >> Re-entry`, `CSM >> Re-entry`.

Exit when **any** of:
- MA5/10 cross over
- MA5/10 leave Low/Top BB and a reverse candle closes
- TF1's own target is reached (its Re-entry, or Top/Low BB)

## 6.2 Take profit by setup

| Setup | TP |
|---|---|
| Extreme | **Mandatory** — MA5/MA10, at most Mid BB |
| MHV | Low BB (sell) / Top BB (buy) — negotiable |
| Re-entry (#1 deck) | TP1 at MA5/10 opposite band, TP2 at Top/Low BB |

## 6.3 Session windows (local time; +1h during DST)

Morning 04:00–05:00 and 08:00–09:00 · Afternoon 12:00–13:00 ·
Evening 16:00–17:00 · Night 20:00–21:00 and 00:00–01:00.

## 6.4 Scalping — 3-minute entry on the hourly candle turn

- Watch the new H1 candle between **XX:00–XX:30**; if no confirmation by
  **XX:50**, wait for the next hourly candle
- H1 green → wait for **Re-entry buy on M3**, once MA5/10 H/L first exit the
  Low BB or sit above MA50
- H1 red → **Re-entry sell on M3**, from Top BB or below MA50
- **Do not enter while MAs are crossing/choppy** — likely sideways

## 6.5 Scalping — CSK on M5 into the M15 candle change

1. M15 changes candle **×2** at Top/Low BB
2. M5 prints a CSK (all-green / all-red) with MA5/10 crossing
3. Take the flow **Re-entry buy on M1** from the moment MA5/10 cross direction

---

# 7. Gaps and Contradictions in the Source Material

**Read this section before anyone tries to implement BBMA.** These are not
nitpicks — several of them decide whether a rule is codeable at all.

## 7.1 MA10L is defined inconsistently

Both Khmer decks list *"Moving average Linear weigh 10 apply to **High**
(MA10L)"* — applying High to a line named "Low". The English manual
(Lesson 4) unambiguously specifies **Apply to: Low**, colour White. The
manual is almost certainly right and the decks carry a copy-paste error,
but this must be confirmed with the operator before coding, because
MA5/10 Low *is* the buy entry band.

## 7.2 "MHV" expands two different ways

- English manual: **Market Hilang Volume** = market *loses* volume
- Khmer decks / cheat-sheet: **Market High Volume** / "Market High/Low Volume"

The manual's meaning (volume exhaustion at the end of a move) is consistent
with every rule attached to it. The decks' expansion appears to be a
mistranslation. The *rules* agree; only the name is in conflict.

## 7.3 "CS Reverse" and "CS Retest" are not numerically defined

This is the **single biggest obstacle to implementation.** Both are central
to Extreme and MHV, and both are described only in prose ("a candle that
stops the move", "price returns to test the highest volume"). No candle-body
ratio, no wick tolerance, no lookback window is given. Any implementation
must *invent* thresholds — which under this project's rules requires an ADR,
and the numbers would be uncalibrated guesses in the ADR-028/030 tradition.

## 7.4 Extreme is defined two ways

- Manual: **MA5 leaves the BB** (an indicator condition)
- Khmer deck: **3 candles break >> reverse >> retest** (a price-action count)

These are not equivalent. The manual's version is mechanical and codeable;
the deck's "3 candles" is not defined precisely enough to reproduce.

## 7.5 "Volume" is used without a source

MHV and CS Reverse both reference the "highest volume" candle. `price_candles`
carries a `volume` column, but for spot FX/CFD this is broker tick-volume,
not true traded volume — and its meaning differs per provider. Whether
Twelve Data's volume for XAUUSD is usable at all is an open question.

## 7.6 Timeframe coverage vs. this project's quota

The BBMA styles need **three** timeframes read together. Intraday needs
H4+H1+M15; scalping needs H1+M15+M5. This project can currently sustain
**one active symbol** across all timeframes (~751 of Twelve Data's 800
requests/day, ADR-140) — so BBMA is feasible for one symbol, and not for
several, until the market-data provider question is settled.

## 7.7 Nothing here is backtested

The source material contains no win rate, no sample size, no drawdown
figures. The webinar's closing slide asks students to *"Back-test and
follow the signals in the group"* — i.e. validation is left to the reader.
This project has no backtesting capability at all (docs/30 lists it under
Long-Term Vision).

---

# 8. Relationship to This Project

BBMA is directly relevant to the oldest open question in this codebase.

`docs/11_SIGNAL_ENGINE.md` originally specified an independent, weighted
evidence pipeline. ADR-085 superseded that: `SignalEngine` became a thin
wrapper over `AIOrchestratorEngine`, whose recommendation comes from an LLM
and therefore *has no portable formula*. ADR-085 explicitly left the door
open:

> *"If a future need genuinely requires a second, independent recommendation
> source to cross-validate against AI Orchestrator's, that needs its own
> design pass."*

BBMA is exactly such a source: deterministic, reproducible, and testable
without an LLM call. It would also address ADR-145's finding — that entry
levels need to come from market structure rather than a midpoint — since
BBMA specifies its entries (MA5/10 bands) and its stops/targets by rule.

**What already exists that BBMA needs:** Bollinger Bands and EMA are already
computed in `technical_analysis/` (docs/39 indicator reference), candles are
persisted per timeframe, and the multi-timeframe combination has precedent
in ADR-030.

**What does not exist:** linear-weighted MAs applied to High/Low, the
Extreme/MHV/Re-entry state machine, and any notion of a setup that spans
three timeframes simultaneously.

**Not started. No ADR yet. No code.** §7's gaps — particularly 7.1, 7.3 and
7.4 — need operator answers before an implementation spec can be written.

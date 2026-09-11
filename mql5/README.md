# mql5/

MetaTrader 5 Expert Advisor for VC Trading AI (ADR-161). It runs inside
your own MT5 terminal, reads `GET /ea/signals`, and trades the signals
there. The website never places trades and never sees your broker login.

Not part of the `backend`/`frontend` apps. It is compiled in MetaEditor,
and CI does not build it.

## VCTradingEA.mq5

### What it does, every `PollSeconds`

1. Fetches the open signals for `SignalSymbol` with your EA token.
2. For each **active** signal it has never acted on:
   - **Before price reaches the entry**, it places a limit order at the
     signal's entry, with the signal's stop loss and take profit. The order
     expires at the signal's `expires_at` if the broker supports expiry.
   - **After price has reached the entry**, it places a market order
     instead, which gets the entry price or better.
   - **If price is already past the stop or the target**, it skips the
     signal.
3. It cancels its own **unfilled** order when the signal is no longer
   listed, or when the signal expires.
4. It never modifies or closes a **filled** position. The broker closes it
   at the stop loss or take profit.

Signals that are `triggered` never get a new order. Every signal is acted
on at most once, even across a terminal restart. That history is kept in
`MQL5\Files\VCTrading\handled_<login>_<magic>_<dry|live>.txt`.

**A failed request never cancels anything.** Only a successful response
that no longer lists a signal counts as "gone". Expiry is checked on the
local clock, so it still runs when the website is unreachable.

### Inputs

| Input | Default | Meaning |
|---|---|---|
| ApiBaseUrl | `https://vcanalyzetrading.site/api/v1` | Website API |
| EaToken | *(empty)* | From **Settings → MT5 Expert Advisor** |
| PollSeconds | 10 | Seconds between checks; 5 minimum (the website allows 30/min) |
| SignalSymbol | `XAUUSD` | Symbol on the website |
| BrokerSymbol | `XAUUSDc` | Symbol in this terminal |
| DryRun | **true** | Log each order and run the broker's pre-trade check without sending |
| LotSize | 0.01 | Fixed lot for every signal, rounded down to the lot step |
| MaxOpenTrades | 1 | Positions plus pending orders from this EA |
| MagicNumber | 16112026 | Marks this EA's orders |
| DeviationPoints | 50 | Max slippage on market entries |

### Install

1. In MT5, go to **File → Open Data Folder** and copy `VCTradingEA.mq5`
   into `MQL5\Experts\`.
2. Open it in MetaEditor (F4) and press **Compile** (F7). Expect
   "0 errors".
3. In **Tools → Options → Expert Advisors**, tick **Allow WebRequest for
   listed URL** and add `https://vcanalyzetrading.site`. Without this,
   every check fails with "URL not allowed".
4. Open an `XAUUSDc` chart. Any timeframe works, because the EA runs on a
   timer rather than on candles.
5. Drag **VCTradingEA** onto the chart and paste your token into
   **EaToken**. Leave **DryRun = true**.
6. Watch the **Experts** tab. On startup you should see
   `VC Trading EA started - DRY RUN`. For every new signal you should see a
   `[DRY RUN] ... broker check: ...` line. The chart's top-left corner
   shows the feed status.

### Going live

Only after the dry-run lines look right: the correct direction, prices,
lot size and expiry.

1. Fund the account. A zero balance makes every broker check fail with
   "no money".
2. Turn on **Algo Trading** in the toolbar, and tick **Allow Algo Trading**
   in the EA's Common tab.
3. Set **DryRun = false**. Live mode keeps a separate history file, so
   signals that are still active get traded.

### Do not

- **Run it on two terminals for the same account.** Each keeps its own
  history, so both would trade every signal.
- **Enable the server-side MetaApi executor** (`EXECUTION_ENABLED`)
  against the same account. That would also double every trade.
- **Use it in the Strategy Tester.** MT5 does not allow `WebRequest`
  there.

### Known limits

- **The website cannot see what the EA did.** Until the report-back
  (ADR-161 Phase C) exists, check MT5's Trade and History tabs.
- **Signal prices come from Twelve Data; fills come from your broker.**
  They differ by the spread and feed differences. The website can mark a
  signal `triggered` while your limit order is still unfilled, or the
  reverse.
- **A broker timeout is never retried.** The order may exist anyway, so
  check the Trade tab when the log says so.

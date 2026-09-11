# mql5/

MetaTrader 5 Expert Advisor for VC Trading AI. It runs inside your own MT5
terminal, reads `GET /ea/signals`, and trades the signals there (ADR-161).
It reports what it did back to the website (ADR-162). The website never
places trades and never sees your broker login.

It is not part of the `backend`/`frontend` apps. You compile it in
MetaEditor, and CI does not build it.

## VCTradingEA.mq5 (version 1.10)

### What it does, every `PollSeconds`

1. **Fetches the open signals** for `SignalSymbol` using your EA token.
2. **Places an order for each active signal it has never acted on:**
   - If price has not reached the entry yet, it places a **limit order**
     at the signal's entry, with the signal's stop loss and take profit.
     The order expires at the signal's `expires_at` if the broker supports
     expiry.
   - If price has already reached the entry, it places a **market order**,
     which fills at the entry price or better.
   - If price is already past the stop or the target, it **skips** the
     signal.
3. **Cancels its own unfilled order** when the signal is no longer listed,
   or when the signal expires.
4. **Never modifies or closes a filled position.** The broker closes it at
   the stop loss or take profit.
5. **Finds fills and closes in MT5's own trade history**, including ones
   that happened while the EA or MT5 was not running.
6. **Reports all of the above to the website** (the EA Activity page, and
   the "MT5 Expert Advisor" card on each signal's page).

Signals that are `triggered` never get a new order. Each signal is acted
on at most once, even across a terminal restart.

**A failed request never cancels anything.** Only a successful response
that no longer lists a signal counts as "gone". Expiry and fills are
checked from this terminal's own clock and history, so those checks still
run when the website is unreachable.

### Files it keeps

The files live in `MQL5\Files\VCTrading\`, with separate copies for dry
run and live:

| File | Holds |
|---|---|
| `handled_<login>_<magic>_<dry\|live>.txt` | Which signals were acted on, plus order and position tickets |
| `reports_<login>_<magic>_<dry\|live>.txt` | Activity reports not yet sent |

Reports are sent in batches of up to 50 after each successful feed check.
If the website is down, they wait in the file, up to 500; beyond that the
oldest are dropped. The website stores each report once, however many
times it is re-sent.

### Inputs

| Input | Default | Meaning |
|---|---|---|
| ApiBaseUrl | `https://vcanalyzetrading.site/api/v1` | Website API |
| EaToken | *(empty)* | From **Settings → MT5 Expert Advisor** |
| PollSeconds | 10 | Seconds between checks. Minimum 5; the website allows 30 per minute |
| ReportActivity | true | Send what the EA does to the website |
| SignalSymbol | `XAUUSD` | Symbol on the website |
| BrokerSymbol | `XAUUSDc` | Symbol in this terminal |
| DryRun | **true** | Log each order and run the broker's pre-trade check, without sending |
| LotSize | 0.01 | Fixed lot for every signal, rounded down to the lot step |
| MaxOpenTrades | 1 | Positions plus pending orders from this EA |
| MagicNumber | 16112026 | Marks this EA's orders |
| DeviationPoints | 50 | Max slippage on market entries |

### Install

1. In MT5, go to **File → Open Data Folder** and copy `VCTradingEA.mq5`
   into `MQL5\Experts\`.
2. Open it in MetaEditor (F4) and press **Compile** (F7). Expect
   "0 errors".
3. Go to **Tools → Options → Expert Advisors**, tick **Allow WebRequest
   for listed URL**, and add `https://vcanalyzetrading.site`. Without this
   step, every check fails with "URL not allowed".
4. Open an `XAUUSDc` chart. Any timeframe works, because the EA runs on a
   timer, not on candles.
5. Drag **VCTradingEA** onto the chart and paste your token into
   **EaToken**. Leave **DryRun = true**.
6. Check that it started:
   - The **Experts** tab shows `VC Trading EA 1.10 started - DRY RUN`, then
     `feed: connected, reading signals`.
   - Each new signal adds a `[DRY RUN] ... broker check: ...` line, and the
     same check appears on the website's **EA Activity** page.

**Upgrading from 1.00:** recompile and re-attach. The existing history
file is read as-is.

### Going live

Only switch to live once the dry-run checks look right: correct direction,
prices, lot size and expiry.

1. Fund the account. With a zero balance, every broker check fails with
   "no money".
2. Turn on **Algo Trading** in the toolbar, and tick **Allow Algo Trading**
   on the EA's Common tab.
3. Set **DryRun = false**. Live mode keeps separate files, so signals that
   are still active get traded.

### Do not

- **Run it on two terminals for the same account.** Each keeps its own
  history, so both would trade every signal.
- **Enable the server-side MetaApi executor** (`EXECUTION_ENABLED`) for the
  same account. That would double every trade too.
- **Use it in the Strategy Tester.** MT5 does not allow `WebRequest`
  there.

### Known limits

- **Signal prices come from Twelve Data; fills come from your broker.**
  They differ by the spread and by feed differences. The website can mark
  a signal `triggered` while your limit order is unfilled, or the reverse.
  EA activity is the account's record and never changes a signal's status.
- **A broker timeout is never retried**, because the order may exist
  anyway. It is reported as rejected with a note to check the Trade tab.

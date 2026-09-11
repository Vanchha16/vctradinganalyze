# mql5/

MetaTrader 5 Expert Advisor for VC Trading AI. It runs inside your own MT5
terminal, reads `GET /ea/signals` and trades the signals there (ADR-161).
It reports what it did back to the website (ADR-162), and takes its
trading settings from the website within limits you set on the terminal
(ADR-163). The website never places trades and never sees your broker
login.

This folder is not part of the `backend`/`frontend` apps. Compile the EA
in MetaEditor; CI does not build it.

## VCTradingEA.mq5 (version 1.20)

### What it does, every `PollSeconds`

1. **Fetches** the open signals for `SignalSymbol`, plus this terminal's
   website settings, using your EA token.
2. **Places an order** for each **active** signal it has not yet acted on
   in the current mode:
   - price has not reached the entry: a **limit order** at the signal's
     entry, with its stop loss and take profit. It expires at the signal's
     `expires_at` if the broker supports expiry.
   - price has already reached the entry: a **market order** at the entry
     or a better price.
   - price is already past the stop or target: **skips** the signal.
3. **Cancels its own unfilled order** when the signal is no longer listed,
   when it expires, or when trading is paused from the website.
4. **Never modifies or closes a filled position.** The broker closes it at
   the stop loss or take profit.
5. **Finds fills and closes** in MT5's own trade history, including ones
   that happened while the EA or MT5 was not running.
6. **Reports all of the above to the website**: the EA Activity page, and
   the "MT5 Expert Advisor" card on each signal's page.

Signals that are `triggered` never get a new order. Each signal is acted
on at most once per mode, even across a terminal restart.

**A failed request never cancels anything.** Only a successful response
that no longer lists a signal counts as "gone". Expiry, pause and fills
are checked from this terminal's own clock, history and last-known
settings, so they still run when the website is unreachable.

### Settings from the website

In **Settings → MT5 Expert Advisor → Settings** on the website you can
change:

| Setting | Notes |
|---|---|
| Trading: Active / Paused | Paused: no new orders, and the EA's unfilled orders are cancelled |
| Mode: Dry run / Live | Live is only honoured when **AllowWebsiteLive = true** on this EA |
| Lot size | Never above **MaxLotSize** on this EA |
| Max open trades | 1-20 |
| Max slippage | 0-1000 points |

The EA applies a change on its next check (about 10 seconds). The website
then shows **Settings applied**. The last settings received are saved, so a
restart while the website is down keeps them.

### Safety limits: only on this terminal

The website can never override these:

| Input | Default | Meaning |
|---|---|---|
| MaxLotSize | 0.10 | Hard lot limit. Any lot from the website or the inputs is capped here |
| AllowWebsiteLive | **false** | Allow the website to switch this EA to live. While false, a live request from the website is ignored and the EA stays in dry run |

A stolen website login can therefore pause the EA, lower its lot or put it
back in dry run. It cannot make the EA riskier than these two inputs
allow.

### All inputs

| Input | Default | Meaning |
|---|---|---|
| ApiBaseUrl | `https://vcanalyzetrading.site/api/v1` | Website API |
| EaToken | *(empty)* | From **Settings → MT5 Expert Advisor** |
| PollSeconds | 10 | Seconds between checks. Minimum 5; the website allows 30 per minute |
| ReportActivity | true | Send what the EA does to the website |
| SignalSymbol | `XAUUSD` | Symbol on the website |
| BrokerSymbol | `XAUUSDc` | Symbol in this terminal |
| MaxLotSize | 0.10 | See safety limits |
| AllowWebsiteLive | false | See safety limits |
| UseWebsiteSettings | true | Take settings from the website. When false, only the inputs below are used |
| DryRun | **true** | Used until website settings arrive |
| LotSize | 0.01 | Used until website settings arrive, rounded down to the lot step |
| MaxOpenTrades | 1 | Used until website settings arrive |
| DeviationPoints | 50 | Used until website settings arrive |
| MagicNumber | 16112026 | Marks this EA's orders. Never change it while the EA has open orders |

### Files it keeps

All in `MQL5\Files\VCTrading\`:

| File | Holds |
|---|---|
| `handled_<login>_<magic>.txt` | Which signals were acted on in which mode, with order and position tickets |
| `reports_<login>_<magic>.txt` | Activity reports not yet sent (at most 500; the oldest are dropped) |
| `settings_<login>_<magic>.txt` | The last website settings received |

On its first start, 1.20 merges the 1.10 files (`..._dry.txt` /
`..._live.txt`) into these.

### Install or upgrade

1. In MT5, open **File → Open Data Folder** and copy `VCTradingEA.mq5`
   into `MQL5\Experts\`.
2. Open it in MetaEditor (F4) and press **Compile** (F7). You should see
   "0 errors".
3. In **Tools → Options → Expert Advisors**, tick **Allow WebRequest for
   listed URL** and add `https://vcanalyzetrading.site`.
4. Open an `XAUUSDc` chart. The timeframe does not matter.
5. Drag **VCTradingEA** onto the chart and paste your token into
   **EaToken**. Review **MaxLotSize** and **AllowWebsiteLive**.
6. Check that it started:
   - The **Experts** tab shows `VC Trading EA 1.20 started`, then
     `feed: connected, reading signals`.
   - On the website, the token shows **EA 1.20** and **Settings applied**.

When upgrading, remove the old EA from the chart before attaching 1.20.
Its history carries over.

### Going live

Only after checking the dry-run reports on the EA Activity page:

1. **Log in to MT5 with the trading password, not the investor
   password.** The window title must not say "Read Only".
2. Make sure the account is funded, and **Algo Trading** is on.
3. Choose where you switch to live:
   - **From MT5:** set **DryRun = false** in the inputs.
   - **From the website:** set **AllowWebsiteLive = true** in the inputs
     (once), then choose **Mode: Live** on the website and confirm.

### Do not

- **Run it on two terminals for the same account.** Each keeps its own
  history, so both would trade every signal.
- **Enable the server-side MetaApi executor** (`EXECUTION_ENABLED`) for the
  same account. That would also double every trade.
- **Use it in the Strategy Tester.** MT5 does not allow `WebRequest`
  there.

### Known limits

- **Signal prices come from Twelve Data; fills come from your broker.**
  They differ by the spread and by feed differences. The website can mark a
  signal `triggered` while your limit order is still unfilled, or the
  reverse. EA activity is the account's own record and never changes a
  signal's status.
- **A broker timeout is never retried.** The order may exist anyway, so it
  is reported as rejected with a note to check the Trade tab.

# pinescript/

TradingView Pine Script indicators for ClaudeTrading AI. These run entirely
inside TradingView's own charting engine - they are not part of the
`backend`/`frontend` apps and have no build step.

## claudetrading_technical_score.pine

Ports `backend/app/services/technical_analysis/scoring_engine.py` (ADR-028)
to Pine Script v6: the same 100-point trend/momentum/oscillator/volume/
volatility/support-resistance formula, minus the conflict penalties, plotted
as a single oscillator on the chart.

**This is a parallel re-implementation, not a live connection to the
backend.** It will only agree with `GET /analysis/technical/{symbol}` when
fed comparable OHLCV history, and can silently drift if either side's
formula changes without the other being updated. If the backend formula
changes, this file needs a matching update (and vice versa) - there is no
automated check that keeps them in sync.

### Install

1. Open the symbol/timeframe you want in TradingView.
2. Pine Editor → New blank indicator → paste the contents of
   `claudetrading_technical_score.pine` → Save → Add to chart.

### Alerts

The script defines two `alertcondition()`s ("ClaudeTrading Bullish Signal" /
"ClaudeTrading Bearish Signal") with a draft JSON alert message. To use them:
right-click the chart → Add Alert → Condition → pick one of the two, set
"Once Per Bar Close" (recommended, avoids intrabar repainting), and add a
webhook URL under Notifications if you want TradingView to POST it
somewhere.

**Update (2026-09-09, ADR-146): the webhook receiver now exists.**
`POST /webhooks/tradingview/{token}` accepts these alerts, stores them in
`tradingview_alerts`, and forwards them to Telegram. It is disabled by
default - set `TRADINGVIEW_WEBHOOK_SECRET` in `backend/.env` and point the
alert's webhook URL at `https://<host>/api/v1/webhooks/tradingview/<secret>`.
Until that secret is set the route returns 404.

An accepted alert is **recorded and notified, never traded**: it does not
create a `Signal` and cannot place a broker order. See ADR-146 for the
trust-boundary reasoning, including why the secret travels in the URL.

The paragraph below described the state before that endpoint existed and is
kept for context:

**There was previously no webhook receiver in the backend for this.** Nothing
in `backend/app/api` accepts an inbound TradingView alert today - the
Telegram delivery pipeline (`signal_tasks.py` → `telegram_tasks.py`) only
fires for signals the backend's own Signal Engine generates from its own
market data, not from TradingView alerts. If you want a TradingView alert to
actually reach the Telegram bot, that needs a new backend endpoint (to
receive and authenticate the webhook payload) plus an ADR, since it's a new
inbound trust boundary - not something to wire up silently. The JSON draft
above is a placeholder shape, not an agreed contract; a real endpoint's
request schema should drive it, not the reverse.

## claudetrading_signals.pine

A companion `overlay=true` script that plots **BUY/SELL labels with
ATR-based stop-loss/take-profit** directly on the price chart, using the
same score/crossover logic as `claudetrading_technical_score.pine` (the two
files duplicate that formula rather than sharing it - Pine has no local-file
import, so if the scoring formula changes, both files need updating by
hand).

**This is a self-contained technical-only heuristic, not a port of the
backend's real signal logic.** The backend's actual BUY/SELL recommendation
and entry/stop-loss/take-profit prices (`signal_engine.py`) come from
`AIOrchestratorEngine` - an LLM call reasoning over Technical Analysis + SMC
+ Confidence + News Sentiment + Economic Calendar together (docs/07,
docs/50). That reasoning step has no portable formula, so this script's
output will **not** match what the backend/Telegram bot actually sends for
the same symbol/timeframe. Stop-loss/take-profit here are just
`entry ± N × ATR(14)` (configurable multiples, default 1.5×/3×, i.e. a 2:1
reward:risk) - a common standalone heuristic, unrelated to the backend's
risk management engine.

Install the same way as the score indicator. Alerts: "CT Heuristic BUY" /
"CT Heuristic SELL", same webhook caveat as above applies.

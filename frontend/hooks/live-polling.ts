import type { Timeframe } from "@/services/types";

//: M1/M5 are the only timeframes Celery Beat's `collect_market_data_task`
//: refreshes often enough (every 60s/300s, `market_data_tasks.py`) for
//: polling to actually show new data - anything H1+ would just re-fetch
//: the same rows. This is a plain DB read (`GET /market/{symbol}/candles`),
//: not an external provider call, so it costs nothing against the
//: Twelve Data quota (docs/40) unlike calling the provider directly would.
export const LIVE_TIMEFRAMES: ReadonlySet<Timeframe> = new Set(["m1", "m5"]);
export const LIVE_POLL_INTERVAL_MS = 15_000;

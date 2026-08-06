"use client";

import { useQuery } from "@tanstack/react-query";

import { getCandles } from "@/services/market-data";
import type { Timeframe } from "@/services/types";

import { LIVE_POLL_INTERVAL_MS, LIVE_TIMEFRAMES } from "./live-polling";

export function useCandles(symbol: string | null, timeframe: Timeframe | null, limit?: number) {
  const isLive = Boolean(timeframe && LIVE_TIMEFRAMES.has(timeframe));
  return useQuery({
    queryKey: ["candles", symbol, timeframe, limit],
    queryFn: () => getCandles(symbol as string, timeframe as Timeframe, { limit }),
    enabled: Boolean(symbol && timeframe),
    refetchInterval: isLive ? LIVE_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: false,
  });
}

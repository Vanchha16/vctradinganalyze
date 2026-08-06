"use client";

import { useQuery } from "@tanstack/react-query";

import { getLatestCandle } from "@/services/market-data";
import type { Timeframe } from "@/services/types";

import { LIVE_POLL_INTERVAL_MS, LIVE_TIMEFRAMES } from "./live-polling";

export function useLatestCandle(symbol: string | null, timeframe: Timeframe | null) {
  const isLive = Boolean(timeframe && LIVE_TIMEFRAMES.has(timeframe));
  return useQuery({
    queryKey: ["latest-candle", symbol, timeframe],
    queryFn: () => getLatestCandle(symbol as string, timeframe as Timeframe),
    enabled: Boolean(symbol && timeframe),
    refetchInterval: isLive ? LIVE_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: false,
  });
}

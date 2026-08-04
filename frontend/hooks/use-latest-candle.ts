"use client";

import { useQuery } from "@tanstack/react-query";

import { getLatestCandle } from "@/services/market-data";
import type { Timeframe } from "@/services/types";

export function useLatestCandle(symbol: string | null, timeframe: Timeframe | null) {
  return useQuery({
    queryKey: ["latest-candle", symbol, timeframe],
    queryFn: () => getLatestCandle(symbol as string, timeframe as Timeframe),
    enabled: Boolean(symbol && timeframe),
  });
}

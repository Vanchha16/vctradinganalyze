"use client";

import { useQuery } from "@tanstack/react-query";

import { getCandles } from "@/services/market-data";
import type { Timeframe } from "@/services/types";

export function useCandles(symbol: string | null, timeframe: Timeframe | null, limit?: number) {
  return useQuery({
    queryKey: ["candles", symbol, timeframe, limit],
    queryFn: () => getCandles(symbol as string, timeframe as Timeframe, { limit }),
    enabled: Boolean(symbol && timeframe),
  });
}

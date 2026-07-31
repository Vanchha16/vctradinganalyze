"use client";

import { useQuery } from "@tanstack/react-query";

import { getMarketRegime } from "@/services/analysis";
import type { Timeframe } from "@/services/types";

export function useMarketRegime(symbol: string | null, timeframe: Timeframe | null) {
  return useQuery({
    queryKey: ["market-regime", symbol, timeframe],
    queryFn: () => getMarketRegime(symbol as string, timeframe as Timeframe),
    enabled: Boolean(symbol && timeframe),
  });
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { getSmcAnalysis } from "@/services/analysis";
import type { Timeframe } from "@/services/types";

export function useSmcAnalysis(symbol: string | null, timeframe: Timeframe | null) {
  return useQuery({
    queryKey: ["smc-analysis", symbol, timeframe],
    queryFn: () => getSmcAnalysis(symbol as string, timeframe as Timeframe),
    enabled: Boolean(symbol && timeframe),
  });
}

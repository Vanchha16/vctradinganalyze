"use client";

import { useQuery } from "@tanstack/react-query";

import { getTechnicalAnalysis } from "@/services/analysis";
import type { Timeframe } from "@/services/types";

export function useTechnicalAnalysis(symbol: string | null, timeframe: Timeframe | null) {
  return useQuery({
    queryKey: ["technical-analysis", symbol, timeframe],
    queryFn: () => getTechnicalAnalysis(symbol as string, timeframe as Timeframe),
    enabled: Boolean(symbol && timeframe),
  });
}

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { generateAiAnalysis } from "@/services/ai-analysis";
import type { Timeframe } from "@/services/types";

export function useGenerateAiAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      symbol,
      timeframe,
      eventId,
    }: {
      symbol: string;
      timeframe: Timeframe;
      eventId?: string;
    }) => generateAiAnalysis(symbol, timeframe, eventId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai-analysis-history"] });
    },
  });
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { getAiAnalysisHistory } from "@/services/ai-analysis";

export function useAiAnalysisHistory(params: { symbol?: string; page?: number; limit?: number }) {
  return useQuery({
    queryKey: ["ai-analysis-history", params],
    queryFn: () => getAiAnalysisHistory(params),
  });
}

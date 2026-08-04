"use client";

import { useQuery } from "@tanstack/react-query";

import { getAiAnalysisById } from "@/services/ai-analysis";

export function useAiAnalysis(id: string | null) {
  return useQuery({
    queryKey: ["ai-analysis", id],
    queryFn: () => getAiAnalysisById(id as string),
    enabled: Boolean(id),
  });
}

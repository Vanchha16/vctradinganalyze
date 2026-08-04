import { apiGet, apiPost } from "@/services/api-client";
import type { AIAnalysisListResponse, AIAnalysisResponse, Timeframe } from "@/services/types";

export function generateAiAnalysis(symbol: string, timeframe: Timeframe): Promise<AIAnalysisResponse> {
  return apiPost<AIAnalysisResponse>(`/analysis/ai/${symbol}`, undefined, { timeframe });
}

export function getAiAnalysisById(id: string): Promise<AIAnalysisResponse> {
  return apiGet<AIAnalysisResponse>(`/analysis/ai/${id}`);
}

export function getAiAnalysisHistory(params: {
  symbol?: string;
  page?: number;
  limit?: number;
}): Promise<AIAnalysisListResponse> {
  return apiGet<AIAnalysisListResponse>("/analysis/history", {
    symbol: params.symbol,
    page: params.page?.toString(),
    limit: (params.limit ?? 20).toString(),
  });
}

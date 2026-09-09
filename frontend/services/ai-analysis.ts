import { apiGet, apiPost } from "@/services/api-client";
import type { AIAnalysisListResponse, AIAnalysisResponse, Timeframe } from "@/services/types";

/** `eventId` (ADR-152) names one economic release for the narration to
 * address - the calendar row the request came from. */
export function generateAiAnalysis(
  symbol: string,
  timeframe: Timeframe,
  eventId?: string,
): Promise<AIAnalysisResponse> {
  return apiPost<AIAnalysisResponse>(`/analysis/ai/${symbol}`, undefined, {
    timeframe,
    ...(eventId ? { event_id: eventId } : {}),
  });
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

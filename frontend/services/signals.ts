import { apiDelete, apiGet, apiPost } from "@/services/api-client";
import type {
  BookmarkResponse,
  SignalGenerationResponse,
  SignalListResponse,
  SignalResponse,
  SignalStatus,
  Timeframe,
} from "@/services/types";

export function generateSignal(symbol: string, timeframe: Timeframe): Promise<SignalGenerationResponse> {
  return apiPost<SignalGenerationResponse>(`/signals/generate/${symbol}`, undefined, { timeframe });
}

export function listSignals(params: {
  symbol?: string;
  status?: SignalStatus;
  page?: number;
  limit?: number;
}): Promise<SignalListResponse> {
  return apiGet<SignalListResponse>("/signals", {
    symbol: params.symbol,
    status: params.status,
    page: params.page?.toString(),
    limit: (params.limit ?? 20).toString(),
  });
}

export function getSignal(id: string): Promise<SignalResponse> {
  return apiGet<SignalResponse>(`/signals/${id}`);
}

export function bookmarkSignal(signalId: string): Promise<BookmarkResponse> {
  return apiPost<BookmarkResponse>("/signals/bookmark", { signal_id: signalId });
}

export function deleteBookmark(bookmarkId: string): Promise<void> {
  return apiDelete(`/signals/bookmark/${bookmarkId}`);
}

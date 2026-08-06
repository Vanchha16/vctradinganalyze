import { apiDelete, apiGet, apiPost, apiPut } from "@/services/api-client";
import type {
  Asset,
  WatchlistAddAssetRequest,
  WatchlistCreateRequest,
  WatchlistDetailResponse,
  WatchlistListResponse,
  WatchlistRenameRequest,
  WatchlistSummaryResponse,
} from "@/services/types";

/**
 * Thin wrappers over `/watchlists*` (docs/58 §2.3, Phase 7D-B) - mirrors
 * `services/admin.ts`'s shape, no business logic here.
 */

export function listWatchlists(): Promise<WatchlistListResponse> {
  return apiGet<WatchlistListResponse>("/watchlists");
}

export function getWatchlist(id: string): Promise<WatchlistDetailResponse> {
  return apiGet<WatchlistDetailResponse>(`/watchlists/${id}`);
}

export function createWatchlist(payload: WatchlistCreateRequest): Promise<WatchlistSummaryResponse> {
  return apiPost<WatchlistSummaryResponse>("/watchlists", payload);
}

export function renameWatchlist(
  id: string,
  payload: WatchlistRenameRequest,
): Promise<WatchlistSummaryResponse> {
  return apiPut<WatchlistSummaryResponse>(`/watchlists/${id}`, payload);
}

export function deleteWatchlist(id: string): Promise<void> {
  return apiDelete<void>(`/watchlists/${id}`);
}

export function addWatchlistAsset(id: string, payload: WatchlistAddAssetRequest): Promise<Asset> {
  return apiPost<Asset>(`/watchlists/${id}/assets`, payload);
}

export function removeWatchlistAsset(id: string, assetId: string): Promise<void> {
  return apiDelete<void>(`/watchlists/${id}/assets/${assetId}`);
}

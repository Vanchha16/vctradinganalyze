"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  addWatchlistAsset,
  createWatchlist,
  deleteWatchlist,
  removeWatchlistAsset,
  renameWatchlist,
} from "@/services/watchlists";
import type {
  WatchlistAddAssetRequest,
  WatchlistCreateRequest,
  WatchlistRenameRequest,
} from "@/services/types";

/** One mutation hook per watchlist action, mirrors
 * `use-admin-user-actions.ts`'s shape (docs/58 §2.3, Phase 7D-B). List and
 * detail invalidations both fire on every mutation - the list needs it
 * for `item_count`/name changes, the detail needs it for asset/name
 * changes - cheap enough at this dataset's scale (BACKLOG.md §24). */

export function useCreateWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WatchlistCreateRequest) => createWatchlist(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useRenameWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: WatchlistRenameRequest }) =>
      renameWatchlist(id, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useDeleteWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteWatchlist(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useAddWatchlistAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: WatchlistAddAssetRequest }) =>
      addWatchlistAsset(id, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useRemoveWatchlistAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, assetId }: { id: string; assetId: string }) => removeWatchlistAsset(id, assetId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

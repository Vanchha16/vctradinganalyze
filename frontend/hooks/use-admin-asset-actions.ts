"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  activateAdminAsset,
  createAdminAsset,
  deactivateAdminAsset,
  updateAdminAsset,
} from "@/services/admin";
import type { AdminAssetCreateRequest, AdminAssetUpdateRequest } from "@/services/types";

/** One mutation hook per admin action, all invalidating the same
 * `["admin-assets"]` query key - mirrors `use-admin-user-actions.ts`'s
 * shape (Phase 9F). */

export function useCreateAdminAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminAssetCreateRequest) => createAdminAsset(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-assets"] }),
  });
}

export function useUpdateAdminAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AdminAssetUpdateRequest }) =>
      updateAdminAsset(id, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-assets"] }),
  });
}

export function useActivateAdminAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => activateAdminAsset(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-assets"] }),
  });
}

export function useDeactivateAdminAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deactivateAdminAsset(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-assets"] }),
  });
}

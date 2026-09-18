"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getRuntimeSettings, updateRuntimeSettings } from "@/services/admin";
import type { RuntimeSettingUpdateRequest } from "@/services/types";

const KEY = ["admin-runtime-settings"];

/** ADR-178 strategy and signal settings. `enabled` gates the request so a
 * non-super-admin never triggers a 403 - the page explains instead. */
export function useRuntimeSettings(enabled: boolean) {
  return useQuery({ queryKey: KEY, queryFn: getRuntimeSettings, enabled });
}

/** Applies one batch. The response is the full new state, so it replaces
 * the cache directly rather than refetching. */
export function useUpdateRuntimeSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RuntimeSettingUpdateRequest) => updateRuntimeSettings(payload),
    onSuccess: (data) => queryClient.setQueryData(KEY, data),
  });
}

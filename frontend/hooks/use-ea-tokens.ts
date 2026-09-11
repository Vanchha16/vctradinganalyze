"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createEaToken, listEaTokens, revokeEaToken, updateEaSettings } from "@/services/ea";
import type { EaSettings } from "@/services/types";

const QUERY_KEY = ["ea-tokens"];

/** Refetches every 15s: after a settings change this is how "waiting for the
 * EA" turns into "applied" without a page reload (ADR-163). */
export function useEaTokens(enabled: boolean) {
  return useQuery({ queryKey: QUERY_KEY, queryFn: listEaTokens, enabled, refetchInterval: 15_000 });
}

export function useCreateEaToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => createEaToken(name),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}

export function useRevokeEaToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => revokeEaToken(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}

export function useUpdateEaSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, settings }: { id: string; settings: EaSettings }) => updateEaSettings(id, settings),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}

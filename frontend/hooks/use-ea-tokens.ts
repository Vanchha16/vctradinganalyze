"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createEaToken, listEaTokens, revokeEaToken } from "@/services/ea";

const QUERY_KEY = ["ea-tokens"];

export function useEaTokens(enabled: boolean) {
  return useQuery({ queryKey: QUERY_KEY, queryFn: listEaTokens, enabled });
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

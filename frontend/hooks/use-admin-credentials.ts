"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { clearApiCredential, listApiCredentials, setApiCredential } from "@/services/admin";

const QUERY_KEY = ["admin-credentials"];

export function useAdminCredentials() {
  return useQuery({ queryKey: QUERY_KEY, queryFn: listApiCredentials });
}

/**
 * Both mutations invalidate the list rather than patching the cache: the
 * server decides the resulting `source` and `hint`, and after a clear it
 * may report the .env fallback as still set. Guessing that locally would
 * show the wrong state.
 */
export function useSetApiCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, value }: { name: string; value: string }) => setApiCredential(name, value),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}

export function useClearApiCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => clearApiCredential(name),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}

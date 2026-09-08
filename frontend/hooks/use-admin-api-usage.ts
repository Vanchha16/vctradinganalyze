"use client";

import { useQuery } from "@tanstack/react-query";

import { getAdminApiUsage } from "@/services/admin";

/**
 * ADR-144. Mirrors `use-admin-logs`/`use-admin-users`' shape.
 *
 * `refetchInterval` is deliberately absent: these are cumulative counters,
 * so polling would only ever show the same numbers creeping upward - and
 * each poll is itself a request this page then counts. Refresh is manual.
 */
export function useAdminApiUsage() {
  return useQuery({
    queryKey: ["admin-api-usage"],
    queryFn: getAdminApiUsage,
  });
}

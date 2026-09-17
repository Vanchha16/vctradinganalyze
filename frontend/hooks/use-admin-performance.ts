"use client";

import { useQuery } from "@tanstack/react-query";

import { getAdminPerformance } from "@/services/admin";

/** ADR-174 signal outcome metrics. No parameters - the epoch is a server
 * setting, not a caller-supplied window. Nothing is cached server-side,
 * so this recomputes on every fetch by design. */
export function useAdminPerformance() {
  return useQuery({
    queryKey: ["admin-performance"],
    queryFn: getAdminPerformance,
  });
}

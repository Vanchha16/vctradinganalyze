"use client";

import { useQuery } from "@tanstack/react-query";

import { getAdminSystemStatus } from "@/services/admin";

/** Shared query key (`ADMIN_SYSTEM_STATUS_QUERY_KEY`) so the maintenance
 * action mutations (`use-admin-maintenance-actions.ts`) can invalidate it
 * after a run and refresh `signals_today`/`ai_analyses_today` without a
 * manual page reload. */
export const ADMIN_SYSTEM_STATUS_QUERY_KEY = ["admin-system-status"];

export function useAdminSystemStatus() {
  return useQuery({
    queryKey: ADMIN_SYSTEM_STATUS_QUERY_KEY,
    queryFn: getAdminSystemStatus,
  });
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { type ListAdminLogsParams, listAdminLogs } from "@/services/admin";

export function useAdminLogs(params: ListAdminLogsParams) {
  return useQuery({
    queryKey: ["admin-logs", params],
    queryFn: () => listAdminLogs(params),
  });
}

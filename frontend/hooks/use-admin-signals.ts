"use client";

import { useQuery } from "@tanstack/react-query";

import { type ListAdminSignalsParams, listAdminSignals } from "@/services/admin";

export function useAdminSignals(params: ListAdminSignalsParams) {
  return useQuery({
    queryKey: ["admin-signals", params],
    queryFn: () => listAdminSignals(params),
  });
}

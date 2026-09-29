"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  getPaperSwingStatistics,
  listPaperSwingTrades,
  type ListPaperSwingTradesParams,
} from "@/services/admin";

/** ADR-182. `enabled` gates the request so a non-super-admin never
 * triggers a 403 - the page explains instead. The record only changes
 * every four hours, so a minute's staleness is harmless. */
export function usePaperSwingStatistics(enabled: boolean) {
  return useQuery({
    queryKey: ["paper-swing-statistics"],
    queryFn: getPaperSwingStatistics,
    enabled,
    staleTime: 60_000,
  });
}

export function usePaperSwingTrades(
  params: ListPaperSwingTradesParams,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["paper-swing-trades", params],
    queryFn: () => listPaperSwingTrades(params),
    enabled,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}

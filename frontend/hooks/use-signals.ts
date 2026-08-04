"use client";

import { useQuery } from "@tanstack/react-query";

import { listSignals } from "@/services/signals";
import type { SignalStatus } from "@/services/types";

export function useSignals(params: {
  symbol?: string;
  status?: SignalStatus;
  page?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["signals", params],
    queryFn: () => listSignals(params),
  });
}

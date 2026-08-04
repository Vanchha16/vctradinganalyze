"use client";

import { useQuery } from "@tanstack/react-query";

import { getSignal } from "@/services/signals";

export function useSignal(id: string | null) {
  return useQuery({
    queryKey: ["signal", id],
    queryFn: () => getSignal(id as string),
    enabled: Boolean(id),
  });
}

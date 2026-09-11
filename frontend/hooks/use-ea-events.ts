"use client";

import { useQuery } from "@tanstack/react-query";

import { type ListEaEventsParams, listEaEvents } from "@/services/ea";

/** Refetches every 30s: the EA reports as it acts, and this is the page you
 * leave open while waiting for a fill. */
export function useEaEvents(params: ListEaEventsParams, enabled = true) {
  return useQuery({
    queryKey: ["ea-events", params],
    queryFn: () => listEaEvents(params),
    enabled,
    refetchInterval: 30_000,
  });
}

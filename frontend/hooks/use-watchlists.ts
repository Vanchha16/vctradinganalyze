"use client";

import { useQuery } from "@tanstack/react-query";

import { listWatchlists } from "@/services/watchlists";

export function useWatchlists() {
  return useQuery({
    queryKey: ["watchlists"],
    queryFn: listWatchlists,
  });
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { getWatchlist } from "@/services/watchlists";

export function useWatchlist(id: string | null) {
  return useQuery({
    queryKey: ["watchlists", "detail", id],
    queryFn: () => getWatchlist(id as string),
    enabled: id !== null,
  });
}

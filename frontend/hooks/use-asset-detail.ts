"use client";

import { useQuery } from "@tanstack/react-query";

import { getAssetBySymbol } from "@/services/market-data";

export function useAssetDetail(symbol: string | null) {
  return useQuery({
    queryKey: ["asset-detail", symbol],
    queryFn: () => getAssetBySymbol(symbol as string),
    enabled: Boolean(symbol),
  });
}

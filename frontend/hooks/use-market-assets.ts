"use client";

import { useQuery } from "@tanstack/react-query";

import { listAssets } from "@/services/market-data";
import type { MarketType } from "@/services/types";

export function useMarketAssets(params: {
  page?: number;
  limit?: number;
  market_type?: MarketType;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ["market-assets", params],
    queryFn: () => listAssets(params),
  });
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { getAssets } from "@/services/analysis";

export function useAssets() {
  return useQuery({
    queryKey: ["assets"],
    queryFn: getAssets,
  });
}

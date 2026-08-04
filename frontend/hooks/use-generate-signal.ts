"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { generateSignal } from "@/services/signals";
import type { Timeframe } from "@/services/types";

export function useGenerateSignal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ symbol, timeframe }: { symbol: string; timeframe: Timeframe }) =>
      generateSignal(symbol, timeframe),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["signals"] });
    },
  });
}

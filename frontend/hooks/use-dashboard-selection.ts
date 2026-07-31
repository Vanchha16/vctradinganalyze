"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

import type { Timeframe } from "@/services/types";

export function useDashboardSelection() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const symbol = searchParams.get("symbol");
  const timeframe = (searchParams.get("timeframe") as Timeframe | null) ?? "h1";

  const setSelection = useCallback(
    (next: { symbol?: string; timeframe?: Timeframe }) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next.symbol !== undefined) params.set("symbol", next.symbol);
      if (next.timeframe !== undefined) params.set("timeframe", next.timeframe);
      router.push(`${pathname}?${params.toString()}`);
    },
    [pathname, router, searchParams],
  );

  return { symbol, timeframe, setSelection };
}

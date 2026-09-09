"use client";

import { useQuery } from "@tanstack/react-query";

import { type ListTradingViewAlertsParams, listTradingViewAlerts } from "@/services/admin";

/** ADR-146. Mirrors `use-admin-logs`' shape. */
export function useTradingViewAlerts(params: ListTradingViewAlertsParams) {
  return useQuery({
    queryKey: ["tradingview-alerts", params],
    queryFn: () => listTradingViewAlerts(params),
  });
}

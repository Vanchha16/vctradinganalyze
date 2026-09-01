"use client";

import { useWebSocket } from "@/hooks/use-websocket";
import type { Timeframe } from "@/services/types";

export interface RealtimeCandleEvent {
  type: "candle";
  symbol: string;
  timeframe: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

interface UseRealtimePricesOptions {
  symbol?: string | null;
  timeframe?: Timeframe;
  onCandleTick?: (candle: RealtimeCandleEvent) => void;
  enabled?: boolean;
}

export function useRealtimePrices({
  symbol,
  timeframe = "m1",
  onCandleTick,
  enabled = true,
}: UseRealtimePricesOptions) {
  const isEnabled = enabled && Boolean(symbol);

  const { status, lastMessage } = useWebSocket<RealtimeCandleEvent>({
    path: "/ws/prices",
    params: {
      symbol: symbol ?? undefined,
      timeframe,
    },
    enabled: isEnabled,
    onMessage: onCandleTick,
  });

  return {
    priceStreamStatus: status,
    latestCandleTick: lastMessage,
  };
}

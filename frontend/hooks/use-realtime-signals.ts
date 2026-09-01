"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "@/hooks/use-websocket";
import { toast } from "@/lib/toast";

export interface RealtimeSignalEvent {
  event: "created" | "status_changed";
  signal_id: string;
  symbol?: string;
  signal_type?: string;
  status: string;
  profit_loss?: number | null;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  confidence?: number | null;
  created_at?: string | null;
  triggered_at?: string | null;
  closed_at?: string | null;
}

export function useRealtimeSignals() {
  const queryClient = useQueryClient();

  const handleMessage = (data: RealtimeSignalEvent) => {
    // Invalidate signals list & specific signal queries
    queryClient.invalidateQueries({ queryKey: ["signals"] });
    if (data.signal_id) {
      queryClient.invalidateQueries({ queryKey: ["signal", data.signal_id] });
    }

    // Display notifications for real-time events
    if (data.event === "created" && data.symbol && data.signal_type) {
      toast.info(`New ${data.signal_type.toUpperCase()} signal created for ${data.symbol}`);
    } else if (data.event === "status_changed") {
      if (data.status === "triggered") {
        toast.info(`Signal entered / triggered for ${data.symbol ?? "asset"}`);
      } else if (data.status === "successful") {
        toast.success(`Signal hit Take Profit! 🎯`);
      } else if (data.status === "stopped_out") {
        toast.error(`Signal hit Stop Loss 🛑`);
      }
    }
  };

  const { status, reconnect } = useWebSocket<RealtimeSignalEvent>({
    path: "/ws/signals",
    onMessage: handleMessage,
  });

  return {
    realtimeStatus: status,
    reconnectSignals: reconnect,
  };
}

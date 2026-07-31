"use client";

import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAssets } from "@/hooks/use-assets";
import { useDashboardSelection } from "@/hooks/use-dashboard-selection";
import type { Timeframe } from "@/services/types";

const TIMEFRAMES: Timeframe[] = ["m1", "m5", "m15", "m30", "h1", "h4", "d1", "w1", "mn"];

export function TopControls({ onRefresh, isFetching }: { onRefresh: () => void; isFetching: boolean }) {
  const { symbol, timeframe, setSelection } = useDashboardSelection();
  const { data: assetsData, isLoading: assetsLoading } = useAssets();

  return (
    <div className="sticky top-0 z-10 flex flex-wrap items-center gap-4 border-b border-border bg-background/95 px-4 py-4 backdrop-blur sm:px-6 lg:px-8">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-muted-foreground">Asset</label>
        <Select
          value={symbol ?? undefined}
          onValueChange={(value) => setSelection({ symbol: value })}
          disabled={assetsLoading}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder={assetsLoading ? "Loading..." : "Select asset"} />
          </SelectTrigger>
          <SelectContent>
            {assetsData?.items.map((asset) => (
              <SelectItem key={asset.id} value={asset.symbol}>
                {asset.symbol}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-muted-foreground">Timeframe</label>
        <Select value={timeframe} onValueChange={(value) => setSelection({ timeframe: value as Timeframe })}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIMEFRAMES.map((tf) => (
              <SelectItem key={tf} value={tf}>
                {tf.toUpperCase()}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-end gap-2 pt-4">
        <Button onClick={onRefresh} disabled={!symbol || isFetching}>
          Analyze
        </Button>
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={!symbol || isFetching} aria-label="Refresh">
          <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {!symbol && !assetsLoading ? (
        <p className="w-full text-xs text-muted-foreground">Select an asset above to run analysis.</p>
      ) : null}
    </div>
  );
}

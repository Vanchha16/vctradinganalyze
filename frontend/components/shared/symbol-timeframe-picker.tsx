"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAssets } from "@/hooks/use-assets";
import type { Timeframe } from "@/services/types";

const TIMEFRAMES: Timeframe[] = ["m1", "m5", "m15", "m30", "h1", "h4", "d1", "w1", "mn"];

/**
 * A symbol + timeframe picker for one-off actions (generate a signal /
 * AI analysis) - local state only, unlike `use-dashboard-selection.ts`'s
 * URL-synced pattern (which is for page-view filters, not action inputs).
 */
export function SymbolTimeframePicker({
  symbol,
  timeframe,
  onSymbolChange,
  onTimeframeChange,
}: {
  symbol: string | null;
  timeframe: Timeframe;
  onSymbolChange: (symbol: string) => void;
  onTimeframeChange: (timeframe: Timeframe) => void;
}) {
  const { data: assetsData, isLoading: assetsLoading } = useAssets();

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-muted-foreground">Asset</label>
        <Select value={symbol ?? undefined} onValueChange={onSymbolChange} disabled={assetsLoading}>
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
        <Select value={timeframe} onValueChange={(value) => onTimeframeChange(value as Timeframe)}>
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
    </div>
  );
}

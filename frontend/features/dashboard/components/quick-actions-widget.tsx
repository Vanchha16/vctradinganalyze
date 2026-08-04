"use client";

import { LineChart, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SymbolTimeframePicker } from "@/components/shared/symbol-timeframe-picker";
import { Button } from "@/components/ui/button";
import { WidgetCard } from "@/features/dashboard/components/widget-card";
import type { Timeframe } from "@/services/types";

/**
 * Sixth dashboard widget - shortcuts into the existing AI Analysis/Signal
 * generate flows (reuses `SymbolTimeframePicker`, zero backend). No
 * natural single "view all" destination, so `WidgetCard`'s `viewAllHref`
 * is omitted.
 */
export function QuickActionsWidget() {
  const router = useRouter();
  const [symbol, setSymbol] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<Timeframe>("h1");

  const query = symbol ? `?symbol=${symbol}&timeframe=${timeframe}` : "";

  return (
    <WidgetCard title="Quick Actions" icon={<Sparkles className="size-4" />}>
      <SymbolTimeframePicker symbol={symbol} timeframe={timeframe} onSymbolChange={setSymbol} onTimeframeChange={setTimeframe} />
      <div className="flex flex-1 flex-col justify-end gap-2 pt-2">
        <Button variant="brand" disabled={!symbol} onClick={() => router.push(`/ai-analysis${query}`)}>
          <Sparkles className="mr-2 h-4 w-4" />
          Generate Analysis
        </Button>
        <Button variant="outline" disabled={!symbol} onClick={() => router.push(`/signals${query}`)}>
          <LineChart className="mr-2 h-4 w-4" />
          Generate Signal
        </Button>
      </div>
    </WidgetCard>
  );
}

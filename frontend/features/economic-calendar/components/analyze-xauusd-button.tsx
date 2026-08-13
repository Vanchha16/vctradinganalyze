"use client";

import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useGenerateAiAnalysis } from "@/hooks/use-generate-ai-analysis";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { EconomicEventImportance } from "@/services/types";

//: Only CRITICAL/HIGH-importance events (the "red folder" events on a
//: calendar like ForexFactory - CPI, NFP, rate decisions) get this
//: shortcut - not every scheduled event. Hardcoded to XAUUSD, not derived
//: from the event's own currency, per explicit operator request (docs/50
//: reasoning already covers cross-asset relevance in its own "economic"
//: section - this button is a fast path to that, not a new analysis).
const ANALYZABLE_IMPORTANCE = new Set<EconomicEventImportance>(["critical", "high"]);
const XAUUSD_SYMBOL = "XAUUSD";
const ANALYSIS_TIMEFRAME = "h1";

export function shouldShowAnalyzeXauusd(importance: EconomicEventImportance): boolean {
  return ANALYZABLE_IMPORTANCE.has(importance);
}

export function AnalyzeXauusdButton() {
  const router = useRouter();
  const generate = useGenerateAiAnalysis();

  async function handleClick() {
    try {
      const result = await generate.mutateAsync({ symbol: XAUUSD_SYMBOL, timeframe: ANALYSIS_TIMEFRAME });
      router.push(`/ai-analysis/${result.id}`);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    }
  }

  return (
    <Button size="sm" variant="secondary" disabled={generate.isPending} onClick={() => void handleClick()}>
      <Sparkles className="size-3.5" />
      {generate.isPending ? "Analyzing..." : "Should I buy or sell XAUUSD?"}
    </Button>
  );
}

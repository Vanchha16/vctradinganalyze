"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { AnalyzeXauusdDialog } from "@/features/economic-calendar/components/analyze-xauusd-dialog";
import { useGenerateAiAnalysis } from "@/hooks/use-generate-ai-analysis";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { AIAnalysisResponse, EconomicEventImportance } from "@/services/types";

//: Only CRITICAL/HIGH-importance events (the "red folder" events on a
//: calendar like ForexFactory - CPI, NFP, rate decisions) get this
//: shortcut - not every scheduled event. Hardcoded to XAUUSD, not derived
//: from the event's own currency, per explicit operator request (docs/50
//: reasoning already covers cross-asset relevance in its own "economic"
//: section - this button is a fast path to that, not a new analysis).
//:
//: ADR-152: the clicked event's id is sent with the request. Without it
//: the backend only saw "XAUUSD, H1" and answered about whatever fell
//: inside its default +24h window - a click on Thursday's CPI came back
//: describing that day's bond auction.
//:
//: ADR-153: the answer opens in a dialog on the calendar instead of
//: navigating to `/ai-analysis/{id}`. Being thrown onto another page to
//: read one sentence, then having to navigate back to compare the next
//: release, made the shortcut slower than the thing it shortcuts.
const ANALYZABLE_IMPORTANCE = new Set<EconomicEventImportance>(["critical", "high"]);
const XAUUSD_SYMBOL = "XAUUSD";
const ANALYSIS_TIMEFRAME = "h1";

export function shouldShowAnalyzeXauusd(importance: EconomicEventImportance): boolean {
  return ANALYZABLE_IMPORTANCE.has(importance);
}

export function AnalyzeXauusdButton({
  eventId,
  eventName,
}: {
  eventId?: string;
  eventName?: string;
}) {
  const generate = useGenerateAiAnalysis();
  const [open, setOpen] = useState(false);
  const [analysis, setAnalysis] = useState<AIAnalysisResponse | null>(null);

  async function handleClick() {
    // Opened before the request resolves, so the dialog itself carries
    // the ~4s wait. Leaving the reader on a "Analyzing..." button with
    // nothing else happening reads as a hang.
    setAnalysis(null);
    setOpen(true);
    try {
      const result = await generate.mutateAsync({
        symbol: XAUUSD_SYMBOL,
        timeframe: ANALYSIS_TIMEFRAME,
        eventId,
      });
      setAnalysis(result);
    } catch (error) {
      // Close on failure: an empty dialog explains nothing, and the
      // toast carries the reason.
      setOpen(false);
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    }
  }

  return (
    <>
      <Button
        size="sm"
        variant="secondary"
        disabled={generate.isPending}
        onClick={() => void handleClick()}
      >
        <Sparkles className="size-3.5" />
        {generate.isPending ? "Analyzing..." : "Should I buy or sell XAUUSD?"}
      </Button>
      <AnalyzeXauusdDialog
        open={open}
        onOpenChange={setOpen}
        eventName={eventName}
        analysis={analysis}
        isPending={generate.isPending}
      />
    </>
  );
}

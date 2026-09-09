"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { confidenceLevelVariant, recommendationVariant, riskLevelVariant } from "@/lib/badge-variants";
import { formatEnumLabel, formatPrice } from "@/lib/format";
import type { AIAnalysisResponse } from "@/services/types";

/**
 * The answer to "Should I buy or sell XAUUSD?", shown in place on the
 * calendar (ADR-153) instead of navigating to `/ai-analysis/{id}`.
 *
 * Deliberately a SUMMARY, not a second copy of the analysis page. It
 * carries the four things that answer the question - the direction, how
 * confident, the levels, and what the model made of this specific
 * release - and links out for the chart, evidence lists and full
 * reasoning. Duplicating the whole page here would mean two places to
 * keep in step.
 *
 * Every displayed field is deterministic and reused verbatim from the
 * response (ADR-078/079); the only model-written text is `reasoning`.
 */
export function AnalyzeXauusdDialog({
  open,
  onOpenChange,
  eventName,
  analysis,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  eventName?: string;
  analysis: AIAnalysisResponse | null;
  isPending: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Should I buy or sell XAUUSD?</DialogTitle>
          <DialogDescription>
            {eventName ? `Around ${eventName} · H1` : "XAUUSD · H1"}
          </DialogDescription>
        </DialogHeader>

        {isPending || analysis === null ? (
          <AnalysisSkeleton />
        ) : (
          <AnalysisBody analysis={analysis} />
        )}

        <DialogFooter className="sm:justify-between">
          {analysis !== null ? (
            <Button asChild variant="secondary" size="sm">
              <Link href={`/ai-analysis/${analysis.id}`}>
                Full analysis
                <ExternalLink className="size-3.5" />
              </Link>
            </Button>
          ) : (
            <span />
          )}
          <Button size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AnalysisSkeleton() {
  return (
    <div className="flex flex-col gap-3 py-2">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-20 w-full" />
      <p className="text-xs text-muted-foreground">
        Running a fresh analysis - this takes a few seconds.
      </p>
    </div>
  );
}

function AnalysisBody({ analysis }: { analysis: AIAnalysisResponse }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={recommendationVariant(analysis.recommendation)} className="text-sm">
          {analysis.recommendation.toUpperCase()}
        </Badge>
        <Badge variant={confidenceLevelVariant(analysis.confidence_level)}>
          {analysis.confidence_score.toFixed(0)}% {formatEnumLabel(analysis.confidence_level)}
        </Badge>
        {analysis.risk_level ? (
          <Badge variant={riskLevelVariant(analysis.risk_level)}>
            {formatEnumLabel(analysis.risk_level)} risk
          </Badge>
        ) : null}
        {/* The recommendation is deterministic, so it stands even when the
            LLM failed - but the prose below is then a template, and the
            reader should know that (ADR-081). */}
        {!analysis.ai_available ? <Badge variant="outline">Narration unavailable</Badge> : null}
      </div>

      {analysis.entry_price ? (
        <dl className="grid grid-cols-3 gap-3 rounded-md border border-border p-3 text-sm">
          <div className="border-l-2 border-primary pl-2.5">
            <dt className="text-xs text-muted-foreground">Entry</dt>
            <dd className="font-medium tabular-nums">{formatPrice(analysis.entry_price)}</dd>
          </div>
          <div className="border-l-2 border-destructive pl-2.5">
            <dt className="text-xs text-muted-foreground">Stop Loss</dt>
            <dd className="font-medium tabular-nums">{formatPrice(analysis.stop_loss)}</dd>
          </div>
          <div className="border-l-2 border-success pl-2.5">
            <dt className="text-xs text-muted-foreground">Take Profit</dt>
            <dd className="font-medium tabular-nums">{formatPrice(analysis.take_profit)}</dd>
          </div>
        </dl>
      ) : (
        <p className="rounded-md border border-border p-3 text-sm text-muted-foreground">
          No trade setup - the recommendation is WAIT.
        </p>
      )}

      {/* The economic section first: it is the one that addresses the
          release the reader clicked on (ADR-152). */}
      {analysis.reasoning.economic ? (
        <Section title={eventSectionTitle(analysis)} body={analysis.reasoning.economic} />
      ) : null}
      <Section title="Summary" body={analysis.reasoning.summary} />
      {analysis.reasoning.risk ? <Section title="Risk" body={analysis.reasoning.risk} /> : null}
    </div>
  );
}

function eventSectionTitle(analysis: AIAnalysisResponse): string {
  return analysis.ai_available ? "What this release means" : "Economic";
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="pt-1 text-sm leading-relaxed">{body}</p>
    </div>
  );
}

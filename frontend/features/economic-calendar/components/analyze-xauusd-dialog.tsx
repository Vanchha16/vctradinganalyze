"use client";

import { AnimatePresence, motion, useReducedMotion, type Variants } from "framer-motion";
import { useEffect, useState } from "react";
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
import { SurpriseBurst } from "@/features/economic-calendar/components/surprise-burst";
import { confidenceLevelVariant, recommendationVariant, riskLevelVariant } from "@/lib/badge-variants";
import { formatEnumLabel, formatPrice } from "@/lib/format";
import type { AIAnalysisResponse } from "@/services/types";

/**
 * The panel bursts in: undersized and tilted, overshooting past its final
 * size before settling. Low `damping` relative to `stiffness` is what
 * produces the bounce - raise damping toward ~26 to calm it down, or drop
 * stiffness to slow the whole thing.
 *
 * Applied to a wrapper INSIDE `DialogContent`, never to `DialogContent`
 * itself: that element is centred with `-translate-x-1/2 -translate-y-1/2`,
 * and a competing transform there is exactly the bug that made the panel
 * fly in from off-centre.
 */
const panelVariants: Variants = {
  hidden: { opacity: 0, scale: 0.72, y: 26, rotate: -2.5 },
  show: {
    opacity: 1,
    scale: 1,
    y: 0,
    rotate: 0,
    transition: { type: "spring", stiffness: 320, damping: 17, mass: 0.85 },
  },
};

const containerVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.12 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.96 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 380, damping: 24, mass: 0.7 },
  },
};

/** The verdict is the answer to the question, so it gets the biggest
 * reveal: from nothing, overshooting well past full size before it
 * settles. `damping: 11` is deliberately springy - this is the one
 * element allowed to look excited. */
const verdictVariants: Variants = {
  hidden: { opacity: 0, scale: 0 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { type: "spring", stiffness: 500, damping: 11, mass: 0.6, delay: 0.06 },
  },
};

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
 *
 * The entrance is a spring-driven reveal: the panel bursts in tilted and
 * undersized, overshoots, and settles; then the verdict pops from nothing
 * before the levels and paragraphs cascade behind it. The eye lands on the
 * answer (BUY/SELL) before any supporting detail exists to distract from
 * it. All of it is spring physics rather than fixed easing - the tunables
 * are `stiffness` (speed) and `damping` (bounce) on each variant below.
 *
 * `useReducedMotion` drops every bit of it to a plain fade, honouring the
 * same preference the `prefers-reduced-motion` block in globals.css does.
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
  const reduced = useReducedMotion();
  // Bumped on each open so the burst remounts and replays; without a
  // changing key it would fire once per page load and never again.
  const [fireKey, setFireKey] = useState(0);

  useEffect(() => {
    if (open) setFireKey((n) => n + 1);
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open ? <SurpriseBurst key={fireKey} fireKey={fireKey} /> : null}
      {/* `duration-300` slows Radix's own fade/zoom. No `slide-*` utility
          here: those emit their own `transform`, which collides with
          DialogContent's `-translate-x-1/2 -translate-y-1/2` centering and
          swings the panel in from off-centre instead of rising. The rise
          is done on the inner wrapper below, where nothing is centred. */}
      <DialogContent className="max-h-[85vh] overflow-y-auto duration-300 sm:max-w-lg">
        <motion.div
          className="flex flex-col gap-4"
          variants={reduced ? undefined : panelVariants}
          initial={reduced ? false : "hidden"}
          animate={reduced ? undefined : "show"}
        >
          <DialogHeader>
            <DialogTitle>Should I buy or sell XAUUSD?</DialogTitle>
            <DialogDescription>
              {eventName ? `Around ${eventName} · H1` : "XAUUSD · H1"}
            </DialogDescription>
          </DialogHeader>

          {/* `mode="wait"` so the skeleton finishes leaving before the
              answer arrives - overlapping them makes the panel jump as
              two different heights occupy the same space. */}
          <AnimatePresence mode="wait" initial={false}>
            {isPending || analysis === null ? (
              <motion.div
                key="skeleton"
                exit={reduced ? undefined : { opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <AnalysisSkeleton />
              </motion.div>
            ) : (
              <AnalysisBody key="body" analysis={analysis} />
            )}
          </AnimatePresence>
        </motion.div>

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
  const reduced = useReducedMotion();

  return (
    <motion.div
      className="flex flex-col gap-4"
      variants={reduced ? undefined : containerVariants}
      initial={reduced ? false : "hidden"}
      animate={reduced ? undefined : "show"}
    >
      <motion.div
        className="flex flex-wrap items-center gap-2"
        variants={reduced ? undefined : itemVariants}
      >
        <motion.span variants={reduced ? undefined : verdictVariants}>
          <Badge variant={recommendationVariant(analysis.recommendation)} className="text-sm">
            {analysis.recommendation.toUpperCase()}
          </Badge>
        </motion.span>
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
      </motion.div>

      {analysis.entry_price ? (
        <motion.dl
          className="grid grid-cols-3 gap-3 rounded-md border border-border p-3 text-sm"
          variants={reduced ? undefined : itemVariants}
        >
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
        </motion.dl>
      ) : (
        <motion.p
          className="rounded-md border border-border p-3 text-sm text-muted-foreground"
          variants={reduced ? undefined : itemVariants}
        >
          No trade setup - the recommendation is WAIT.
        </motion.p>
      )}

      {/* The economic section first: it is the one that addresses the
          release the reader clicked on (ADR-152). */}
      {analysis.reasoning.economic ? (
        <Section
          title={eventSectionTitle(analysis)}
          body={analysis.reasoning.economic}
          reduced={reduced}
        />
      ) : null}
      <Section title="Summary" body={analysis.reasoning.summary} reduced={reduced} />
      {analysis.reasoning.risk ? (
        <Section title="Risk" body={analysis.reasoning.risk} reduced={reduced} />
      ) : null}
    </motion.div>
  );
}

function eventSectionTitle(analysis: AIAnalysisResponse): string {
  return analysis.ai_available ? "What this release means" : "Economic";
}

function Section({
  title,
  body,
  reduced,
}: {
  title: string;
  body: string;
  reduced: boolean | null;
}) {
  return (
    <motion.div variants={reduced ? undefined : itemVariants}>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="pt-1 text-sm leading-relaxed">{body}</p>
    </motion.div>
  );
}

"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RiskReviewResponse } from "@/services/types";

/**
 * ADR-167 - the AI risk manager's approve/veto on a BUY/SELL. Says plainly
 * whether it was allowed to act: a shadow veto did not stop anything, and a
 * reader who assumes it did would misjudge the signal.
 */
export function RiskReviewCard({ review }: { review: RiskReviewResponse }) {
  const vetoed = review.verdict === "veto";
  const Icon = vetoed ? ShieldAlert : ShieldCheck;

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
        <CardTitle className="flex items-center gap-2">
          <Icon className={`size-4 ${vetoed ? "text-destructive" : "text-success"}`} aria-hidden />
          AI risk review
        </CardTitle>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={vetoed ? "destructive" : "success"}>{vetoed ? "Veto" : "Approve"}</Badge>
          <Badge variant="outline">{review.mode === "shadow" ? "Shadow mode · not blocking" : "Enforced"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        <p>
          <span className="text-muted-foreground">Biggest risk: </span>
          {review.key_risk}
        </p>
        <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
          {review.reasons.map((reason) => (
            <li key={reason} className="break-words">
              {reason}
            </li>
          ))}
        </ul>
        {vetoed && review.mode === "shadow" ? (
          <p className="text-xs text-muted-foreground">
            Recorded to compare with the real result - this veto did not stop the signal.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

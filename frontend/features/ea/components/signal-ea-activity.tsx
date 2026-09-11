"use client";

import { Bot } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEaEvents } from "@/hooks/use-ea-events";
import { eaEventVariant } from "@/lib/badge-variants";
import { formatDateTime } from "@/lib/format";

import { describeEaEvent, EA_EVENT_LABELS, formatEaProfit, profitClass } from "./ea-event-text";

/**
 * What the MT5 EA did with this one signal (ADR-162), oldest first so it
 * reads as a story: checked, placed, filled, closed. Separate from
 * `SignalStatusTimeline` on purpose - that one is the signal, this is the
 * account, and the two can legitimately disagree.
 */
export function SignalEaActivity({ signalId }: { signalId: string }) {
  const { data, isLoading, isError } = useEaEvents({ signal_id: signalId, limit: 50 });
  const events = [...(data?.items ?? [])].reverse();

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
        <CardTitle className="flex items-center gap-2">
          <Bot className="size-4 text-primary" aria-hidden />
          MT5 Expert Advisor
        </CardTitle>
        <Link href="/ea-activity" className="focus-ring rounded text-xs text-muted-foreground hover:text-primary">
          All EA activity
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : isError ? (
          <p className="text-sm text-muted-foreground">EA activity is unavailable right now.</p>
        ) : events.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Your EA has not reported anything for this signal. It only acts on signals that are still
            open while it is running.
          </p>
        ) : (
          <ol className="flex flex-col gap-3">
            {events.map((event) => (
              <li key={event.id} className="flex flex-col gap-1 border-l-2 border-border pl-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant={eaEventVariant(event.event_type)}>{EA_EVENT_LABELS[event.event_type]}</Badge>
                  {event.dry_run ? <Badge variant="outline">Dry run</Badge> : <Badge variant="warning">Live</Badge>}
                  <span className="text-xs text-muted-foreground">{formatDateTime(event.occurred_at)}</span>
                </div>
                <p className="break-words text-sm">
                  {describeEaEvent(event)}
                  {formatEaProfit(event) ? (
                    <span className={`ml-2 font-medium tabular-nums ${profitClass(event)}`}>
                      {formatEaProfit(event)}
                    </span>
                  ) : null}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {event.token_name} · {event.account_login} · {event.broker_symbol}
                </p>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}

"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { eaEventVariant, recommendationVariant } from "@/lib/badge-variants";
import { formatDateTime } from "@/lib/format";
import type { EaEventResponse } from "@/services/types";

import { describeEaEvent, EA_EVENT_LABELS, formatEaProfit, profitClass } from "./ea-event-text";

function ModeBadge({ dryRun }: { dryRun: boolean }) {
  return dryRun ? <Badge variant="outline">Dry run</Badge> : <Badge variant="warning">Live</Badge>;
}

function SignalLink({ event }: { event: EaEventResponse }) {
  return (
    <Link
      href={`/signals/${event.signal_id}`}
      className="focus-ring inline-flex items-center gap-1.5 rounded text-[13px] hover:text-primary"
    >
      {event.signal_type ? (
        <Badge variant={recommendationVariant(event.signal_type)}>{event.signal_type.toUpperCase()}</Badge>
      ) : null}
      <span className="font-mono text-xs text-muted-foreground">{event.signal_id.slice(0, 8)}</span>
    </Link>
  );
}

/**
 * ADR-162 EA activity, newest first. A table from `md` up; stacked rows on
 * a phone, where six columns cannot fit.
 */
export function EaEventTable({ events }: { events: EaEventResponse[] }) {
  return (
    <>
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Signal</TableHead>
              <TableHead>Details</TableHead>
              <TableHead className="text-right">Profit</TableHead>
              <TableHead>Terminal</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.map((event) => (
              <TableRow key={event.id}>
                <TableCell className="whitespace-nowrap text-muted-foreground">
                  {formatDateTime(event.occurred_at)}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge variant={eaEventVariant(event.event_type)}>{EA_EVENT_LABELS[event.event_type]}</Badge>
                    <ModeBadge dryRun={event.dry_run} />
                  </div>
                </TableCell>
                <TableCell>
                  <SignalLink event={event} />
                </TableCell>
                <TableCell className="max-w-md text-[13px]">{describeEaEvent(event)}</TableCell>
                <TableCell className={`whitespace-nowrap text-right tabular-nums ${profitClass(event)}`}>
                  {formatEaProfit(event) ?? "—"}
                </TableCell>
                <TableCell className="whitespace-nowrap text-muted-foreground">
                  {event.token_name}
                  <span className="block text-[11px]">{event.account_login}</span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ul className="divide-y divide-border md:hidden">
        {events.map((event) => (
          <li key={event.id} className="flex flex-col gap-2 px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge variant={eaEventVariant(event.event_type)}>{EA_EVENT_LABELS[event.event_type]}</Badge>
                <ModeBadge dryRun={event.dry_run} />
              </div>
              <span className="text-xs text-muted-foreground">{formatDateTime(event.occurred_at)}</span>
            </div>
            <p className="break-words text-sm">{describeEaEvent(event)}</p>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <SignalLink event={event} />
              {formatEaProfit(event) ? (
                <span className={`text-sm font-medium tabular-nums ${profitClass(event)}`}>
                  {formatEaProfit(event)}
                </span>
              ) : (
                <span className="text-xs text-muted-foreground">{event.token_name}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

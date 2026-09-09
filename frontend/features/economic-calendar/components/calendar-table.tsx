import { ArrowDown, ArrowUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AnalyzeXauusdButton,
  shouldShowAnalyzeXauusd,
} from "@/features/economic-calendar/components/analyze-xauusd-button";
import { importanceVariant } from "@/lib/badge-variants";
import {
  formatDateTime,
  formatEconomicValue,
  formatEnumLabel,
} from "@/lib/format";
import type { EconomicEventResponse } from "@/services/types";

function biasLabel(
  marketBias: EconomicEventResponse["market_bias"],
): string | null {
  if (!marketBias) return null;
  const values = Object.values(marketBias);
  return values.length > 0 ? formatEnumLabel(values[0]) : null;
}

export function CalendarTable({
  events,
  sort = "time_asc",
  onSortChange,
}: {
  events: EconomicEventResponse[];
  sort?: string;
  onSortChange?: (next: string) => void;
}) {
  const descending = sort === "time_desc";
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>
            {onSortChange ? (
              <button
                type="button"
                // Sorting is a server round-trip, not a client-side
                // reorder: only the current page is in memory, so
                // sorting here would reorder 25 rows out of hundreds.
                onClick={() =>
                  onSortChange(descending ? "time_asc" : "time_desc")
                }
                className="inline-flex items-center gap-1 hover:text-foreground"
                aria-label={`Sort by time, currently ${descending ? "newest" : "soonest"} first`}
              >
                Time
                {descending ? (
                  <ArrowDown className="h-3 w-3" aria-hidden />
                ) : (
                  <ArrowUp className="h-3 w-3" aria-hidden />
                )}
              </button>
            ) : (
              "Time"
            )}
          </TableHead>
          <TableHead>Currency</TableHead>
          <TableHead>Event</TableHead>
          <TableHead>Importance</TableHead>
          <TableHead>Forecast</TableHead>
          <TableHead>Previous</TableHead>
          <TableHead>Actual</TableHead>
          <TableHead>Bias</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {events.map((event) => {
          const bias = biasLabel(event.market_bias);
          return (
            <TableRow
              key={event.id}
              className={
                event.risk_window
                  ? "bg-warning/10 border-l-2 border-l-warning"
                  : undefined
              }
            >
              <TableCell className="text-muted-foreground">
                {formatDateTime(event.release_time)}
              </TableCell>
              <TableCell className="font-medium">{event.currency}</TableCell>
              <TableCell>{event.event_name}</TableCell>
              <TableCell>
                <Badge variant={importanceVariant(event.importance)}>
                  {formatEnumLabel(event.importance)}
                </Badge>
              </TableCell>
              <TableCell className="tabular-nums">
                {formatEconomicValue(event.forecast, event.unit)}
              </TableCell>
              <TableCell className="tabular-nums">
                {formatEconomicValue(event.previous, event.unit)}
              </TableCell>
              <TableCell className="tabular-nums">
                {formatEconomicValue(event.actual, event.unit)}
              </TableCell>
              <TableCell>
                {bias ? <Badge variant="outline">{bias}</Badge> : "—"}
              </TableCell>
              <TableCell>
                {shouldShowAnalyzeXauusd(event.importance) ? (
                  <AnalyzeXauusdButton />
                ) : null}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

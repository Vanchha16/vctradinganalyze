import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { importanceVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import type { EconomicEventResponse } from "@/services/types";

function biasLabel(marketBias: EconomicEventResponse["market_bias"]): string | null {
  if (!marketBias) return null;
  const values = Object.values(marketBias);
  return values.length > 0 ? formatEnumLabel(values[0]) : null;
}

export function CalendarTable({ events }: { events: EconomicEventResponse[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Time</TableHead>
          <TableHead>Currency</TableHead>
          <TableHead>Event</TableHead>
          <TableHead>Importance</TableHead>
          <TableHead>Forecast</TableHead>
          <TableHead>Previous</TableHead>
          <TableHead>Actual</TableHead>
          <TableHead>Bias</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {events.map((event) => {
          const bias = biasLabel(event.market_bias);
          return (
            <TableRow
              key={event.id}
              className={event.risk_window ? "border-l-2 border-l-warning bg-warning/10" : undefined}
            >
              <TableCell className="text-muted-foreground">{formatDateTime(event.release_time)}</TableCell>
              <TableCell className="font-medium">{event.currency}</TableCell>
              <TableCell>{event.event_name}</TableCell>
              <TableCell>
                <Badge variant={importanceVariant(event.importance)}>{formatEnumLabel(event.importance)}</Badge>
              </TableCell>
              <TableCell className="tabular-nums">{event.forecast ?? "—"}</TableCell>
              <TableCell className="tabular-nums">{event.previous ?? "—"}</TableCell>
              <TableCell className="tabular-nums">{event.actual ?? "—"}</TableCell>
              <TableCell>{bias ? <Badge variant="outline">{bias}</Badge> : "—"}</TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

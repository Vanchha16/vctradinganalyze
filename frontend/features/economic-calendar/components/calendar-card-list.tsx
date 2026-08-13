import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { AnalyzeXauusdButton, shouldShowAnalyzeXauusd } from "@/features/economic-calendar/components/analyze-xauusd-button";
import { importanceVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { EconomicEventResponse } from "@/services/types";

function biasLabel(marketBias: EconomicEventResponse["market_bias"]): string | null {
  if (!marketBias) return null;
  const values = Object.values(marketBias);
  return values.length > 0 ? formatEnumLabel(values[0]) : null;
}

/**
 * Mobile counterpart to `CalendarTable` - same data/props, stacked-card
 * presentation instead of a horizontally-scrolled table. Rendered
 * alongside `CalendarTable` via a `hidden md:block` / `md:hidden` pair in
 * `economic-calendar/page.tsx`, not a replacement. Risk-window
 * highlighting carried over as a left border accent, matching the table.
 */
export function CalendarCardList({ events }: { events: EconomicEventResponse[] }) {
  return (
    <div className="flex flex-col gap-2">
      {events.map((event) => {
        const bias = biasLabel(event.market_bias);
        return (
          <Card
            key={event.id}
            className={cn(event.risk_window && "border-l-2 border-l-warning bg-warning/10")}
          >
            <CardContent className="flex flex-col gap-2 py-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium">{event.event_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {event.currency} · {formatDateTime(event.release_time)}
                  </p>
                </div>
                <Badge variant={importanceVariant(event.importance)}>{formatEnumLabel(event.importance)}</Badge>
              </div>
              <dl className="grid grid-cols-3 gap-2 border-t border-border pt-2 text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground">Forecast</dt>
                  <dd className="tabular-nums">{event.forecast ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Previous</dt>
                  <dd className="tabular-nums">{event.previous ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Actual</dt>
                  <dd className="tabular-nums">{event.actual ?? "—"}</dd>
                </div>
              </dl>
              {bias ? <Badge variant="outline">{bias}</Badge> : null}
              {shouldShowAnalyzeXauusd(event.importance) ? <AnalyzeXauusdButton /> : null}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

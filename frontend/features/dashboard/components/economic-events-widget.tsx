"use client";

import { CalendarClock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { WidgetSkeleton } from "@/components/shared/skeletons";
import { WidgetCard } from "@/features/dashboard/components/widget-card";
import { useUpcomingEvents } from "@/hooks/use-upcoming-events";
import { importanceVariant } from "@/lib/badge-variants";
import { formatDateTime } from "@/lib/format";

export function EconomicEventsWidget() {
  const eventsQuery = useUpcomingEvents();
  const events = eventsQuery.data?.items.slice(0, 5) ?? [];

  return (
    <WidgetCard title="Economic Events" viewAllHref="/economic-calendar" icon={<CalendarClock className="size-4" />}>
      {eventsQuery.isLoading ? (
        <WidgetSkeleton />
      ) : events.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {events.map((event) => (
            <li key={event.id} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-surface/60">
              <div className="min-w-0">
                <p className="truncate font-medium">{event.event_name}</p>
                <p className="text-xs text-muted-foreground">{formatDateTime(event.release_time)}</p>
              </div>
              <Badge variant={importanceVariant(event.importance)}>{event.currency}</Badge>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No upcoming high-impact events.</p>
      )}
    </WidgetCard>
  );
}

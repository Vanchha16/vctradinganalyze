"use client";

import { Zap } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { WidgetSkeleton } from "@/components/shared/skeletons";
import { WidgetCard } from "@/features/dashboard/components/widget-card";
import { useSignals } from "@/hooks/use-signals";
import { recommendationVariant, signalStatusVariant } from "@/lib/badge-variants";
import { formatEnumLabel } from "@/lib/format";

export function LatestSignalsWidget() {
  const signalsQuery = useSignals({ limit: 5 });

  return (
    <WidgetCard title="Latest Signals" viewAllHref="/signals" icon={<Zap className="size-4" />}>
      {signalsQuery.isLoading ? (
        <WidgetSkeleton />
      ) : signalsQuery.data && signalsQuery.data.items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {signalsQuery.data.items.map((signal) => (
            <li key={signal.id}>
              <Link
                href={`/signals/${signal.id}`}
                className="focus-ring flex items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-surface/60"
              >
                <span className="font-medium">
                  {signal.symbol} · {signal.timeframe.toUpperCase()}
                </span>
                <div className="flex items-center gap-1.5">
                  <Badge variant={recommendationVariant(signal.signal_type)}>
                    {signal.signal_type.toUpperCase()}
                  </Badge>
                  <Badge variant={signalStatusVariant(signal.status)}>{formatEnumLabel(signal.status)}</Badge>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No signals yet.</p>
      )}
    </WidgetCard>
  );
}

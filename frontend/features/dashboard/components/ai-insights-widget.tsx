"use client";

import { BrainCircuit } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { WidgetSkeleton } from "@/components/shared/skeletons";
import { WidgetCard } from "@/features/dashboard/components/widget-card";
import { useAiAnalysisHistory } from "@/hooks/use-ai-analysis-history";
import { recommendationVariant } from "@/lib/badge-variants";
import { formatRelativeTime } from "@/lib/format";

export function AiInsightsWidget() {
  const historyQuery = useAiAnalysisHistory({ limit: 5 });

  return (
    <WidgetCard title="AI Insights" viewAllHref="/ai-analysis" icon={<BrainCircuit className="size-4" />}>
      {historyQuery.isLoading ? (
        <WidgetSkeleton />
      ) : historyQuery.data && historyQuery.data.items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {historyQuery.data.items.map((item) => (
            <li key={item.id}>
              <Link
                href={`/ai-analysis/${item.id}`}
                className="focus-ring flex items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-surface/60"
              >
                <span className="font-medium">
                  {item.symbol} · {item.timeframe.toUpperCase()}
                </span>
                <div className="flex items-center gap-2">
                  <Badge variant={recommendationVariant(item.recommendation)}>
                    {item.recommendation.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{formatRelativeTime(item.calculated_at)}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No AI analyses yet.</p>
      )}
    </WidgetCard>
  );
}

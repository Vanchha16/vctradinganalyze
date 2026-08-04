"use client";

import { BarChart3 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { WidgetSkeleton } from "@/components/shared/skeletons";
import { WidgetCard } from "@/features/dashboard/components/widget-card";
import { useMarketAssets } from "@/hooks/use-market-assets";
import { formatEnumLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { MarketType } from "@/services/types";

/** Purely visual category color, not a semantic status - scoped to this widget's row list, not `lib/badge-variants.ts`. */
const MARKET_TYPE_DOT: Record<MarketType, string> = {
  forex: "bg-blue-500",
  metal: "bg-amber-500",
  crypto: "bg-violet-500",
  index: "bg-teal-500",
};

export function MarketOverviewWidget() {
  const assetsQuery = useMarketAssets({ limit: 5, is_active: true });

  return (
    <WidgetCard title="Market Overview" viewAllHref="/markets" icon={<BarChart3 className="size-4" />}>
      {assetsQuery.isLoading ? (
        <WidgetSkeleton />
      ) : assetsQuery.data && assetsQuery.data.items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {assetsQuery.data.items.map((asset) => (
            <li key={asset.id}>
              <Link
                href={`/markets/${asset.symbol}`}
                className="focus-ring flex items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-surface/60"
              >
                <span className="flex items-center gap-2 font-medium">
                  <span className={cn("h-1.5 w-1.5 rounded-full", MARKET_TYPE_DOT[asset.market_type])} aria-hidden />
                  {asset.symbol}
                </span>
                <Badge variant="outline">{formatEnumLabel(asset.market_type)}</Badge>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No assets available.</p>
      )}
    </WidgetCard>
  );
}

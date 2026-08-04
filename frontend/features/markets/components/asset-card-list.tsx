import { LineChart, Sparkles } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { assetActiveVariant } from "@/lib/badge-variants";
import { formatEnumLabel } from "@/lib/format";
import type { Asset } from "@/services/types";

/**
 * Mobile counterpart to `AssetTable` - same data/props, stacked-card
 * presentation instead of a horizontally-scrolled table. Rendered
 * alongside `AssetTable` via a `hidden md:block` / `md:hidden` pair in
 * `markets/page.tsx`, not a replacement.
 */
export function AssetCardList({ assets }: { assets: Asset[] }) {
  return (
    <div className="flex flex-col gap-2">
      {assets.map((asset) => {
        const query = `?symbol=${asset.symbol}&timeframe=h1`;
        return (
          <Card key={asset.id}>
            <CardContent className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <Link href={`/markets/${asset.symbol}`} className="focus-ring rounded text-[13px] font-semibold text-foreground transition-colors hover:text-primary">
                  {asset.symbol}
                </Link>
                <p className="truncate text-[11px] text-muted-foreground">{asset.name}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <Badge variant="outline">{formatEnumLabel(asset.market_type)}</Badge>
                  <Badge variant={assetActiveVariant(asset.is_active)}>
                    {asset.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Link
                  href={`/ai-analysis${query}`}
                  aria-label={`Analyze ${asset.symbol}`}
                  className="focus-ring rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
                >
                  <Sparkles className="h-4 w-4" />
                </Link>
                <Link
                  href={`/signals${query}`}
                  aria-label={`Generate signal for ${asset.symbol}`}
                  className="focus-ring rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
                >
                  <LineChart className="h-4 w-4" />
                </Link>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

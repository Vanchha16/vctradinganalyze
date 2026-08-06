"use client";

import { useMemo, useState } from "react";
import { Star } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { AssetTable, type AssetSortKey } from "@/features/markets/components/asset-table";
import type { Asset } from "@/services/types";

/**
 * The watchlist asset table (docs/58 §2.4) - reuses Markets' `AssetTable`
 * directly rather than a new table, with the additive `onRemove` prop
 * (`asset-table.tsx`) for the one watchlist-specific action Markets
 * doesn't need. Sorting is local component state (no URL persistence,
 * unlike the Markets page) since a single watchlist's asset count is
 * small and this view has no filters/pagination to keep in sync with.
 */
export function WatchlistDetail({
  assets,
  onRemove,
  onAddAsset,
}: {
  assets: Asset[];
  onRemove: (asset: Asset) => void;
  onAddAsset: () => void;
}) {
  const [sort, setSort] = useState<AssetSortKey>("symbol");
  const [order, setOrder] = useState<"asc" | "desc">("asc");

  const sorted = useMemo(() => {
    const direction = order === "asc" ? 1 : -1;
    return [...assets].sort((a, b) => {
      const aValue = a[sort as keyof Asset];
      const bValue = b[sort as keyof Asset];
      if (aValue === bValue) return 0;
      return aValue! > bValue! ? direction : -direction;
    });
  }, [assets, sort, order]);

  function handleSortChange(key: AssetSortKey) {
    if (key === sort) {
      setOrder(order === "asc" ? "desc" : "asc");
    } else {
      setSort(key);
      setOrder("asc");
    }
  }

  if (assets.length === 0) {
    return (
      <EmptyState
        icon={Star}
        title="No assets yet"
        description="Add an asset to start tracking it in this watchlist."
        action={
          <Button size="sm" onClick={onAddAsset}>
            Add asset
          </Button>
        }
      />
    );
  }

  return (
    <AssetTable
      assets={sorted}
      sort={sort}
      order={order}
      onSortChange={handleSortChange}
      onRemove={onRemove}
    />
  );
}

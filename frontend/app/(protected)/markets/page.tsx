"use client";

import { useEffect, useMemo, useState } from "react";

import { BarChart3, Layers } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader, Tag } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { AssetCardList } from "@/features/markets/components/asset-card-list";
import { AssetFilterBar, type AssetFilters } from "@/features/markets/components/asset-filter-bar";
import { AssetTable, type AssetSortKey } from "@/features/markets/components/asset-table";
import { MarketDetailPanel } from "@/features/markets/components/market-detail-panel";
import { useMarketAssets } from "@/hooks/use-market-assets";
import { useQueryFilters } from "@/hooks/use-query-filters";
import type { Asset } from "@/services/types";

const DEFAULT_FILTERS: AssetFilters = {
  market_type: undefined,
  is_active: undefined,
  search: undefined,
  sort: "symbol",
  order: "asc",
};

const PAGE_SIZE = 20;

/**
 * Backend `/assets` has no `sort`/`search` query param and this dataset
 * is dev-scale, so the full active+inactive set is fetched once
 * (`limit: 100`, same endpoint `useMarketAssets` already called) and
 * filtered/sorted/paginated client-side instead of faking server-side
 * behavior that doesn't exist.
 *
 * Desktop (`xl:` and up) is a master-detail workspace: the screener on
 * the left, a `MarketDetailPanel` preview on the right that updates on
 * row selection - client-side state only, no new route, no change to
 * `/markets/[symbol]` which remains fully reachable (via the symbol
 * link and the panel's "Open full page" link). Below `xl:` the page is
 * unchanged - the existing table/card list navigates straight to
 * `/markets/[symbol]` as before.
 */
export default function MarketsPage() {
  const { filters, page, setFilters, setPage } = useQueryFilters(DEFAULT_FILTERS);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  const assetsQuery = useMarketAssets({ limit: 100 });

  const sort = (filters.sort as AssetSortKey) ?? "symbol";
  const order = (filters.order as "asc" | "desc") ?? "asc";

  const filtered = useMemo(() => {
    const items = assetsQuery.data?.items ?? [];
    const search = filters.search?.trim().toLowerCase();

    let result = items.filter((asset) => {
      if (filters.market_type && asset.market_type !== filters.market_type) return false;
      if (filters.is_active !== undefined && String(asset.is_active) !== filters.is_active) return false;
      if (search && !asset.symbol.toLowerCase().includes(search) && !asset.name.toLowerCase().includes(search)) {
        return false;
      }
      return true;
    });

    result = [...result].sort((a, b) => {
      const direction = order === "asc" ? 1 : -1;
      const aValue: string | boolean = a[sort as keyof Asset] as string | boolean;
      const bValue: string | boolean = b[sort as keyof Asset] as string | boolean;
      if (aValue === bValue) return 0;
      return aValue > bValue ? direction : -direction;
    });

    return result;
  }, [assetsQuery.data, filters.market_type, filters.is_active, filters.search, sort, order]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Default the desktop preview panel to the first visible row once data
  // has loaded, and drop the selection if it scrolls out of the current
  // filtered/paginated set.
  useEffect(() => {
    if (pageItems.length === 0) {
      setSelectedSymbol(null);
      return;
    }
    if (!pageItems.some((asset) => asset.symbol === selectedSymbol)) {
      setSelectedSymbol(pageItems[0]!.symbol);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageItems]);

  function handleSortChange(key: AssetSortKey) {
    if (key === sort) {
      setFilters({ order: order === "asc" ? "desc" : "asc" }, { resetPage: false });
    } else {
      setFilters({ sort: key, order: "asc" }, { resetPage: false });
    }
  }

  return (
    <div>
      <PageContainer>
        <PageHeader title="Markets" description="Browse supported assets across forex, metals, crypto, and indices." />
        <AssetFilterBar filters={filters} onChange={(next) => setFilters(next)} />
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.6fr_1fr]">
          <Panel>
            <PanelHeader
              title="Screener results"
              subtitle={`${filtered.length} instruments match`}
              icon={<Layers className="size-4" />}
              right={<Tag tone="brand">Live</Tag>}
            />
            {assetsQuery.isLoading ? (
              <div className="p-4">
                <Skeleton className="h-96 w-full" />
              </div>
            ) : assetsQuery.isError ? (
              <ErrorCard error={assetsQuery.error} onRetry={() => assetsQuery.refetch()} />
            ) : pageItems.length > 0 ? (
              <>
                <div className="hidden md:block">
                  <AssetTable
                    assets={pageItems}
                    sort={sort}
                    order={order}
                    onSortChange={handleSortChange}
                    selectedSymbol={selectedSymbol}
                    onSelectSymbol={setSelectedSymbol}
                  />
                </div>
                <div className="p-3 md:hidden">
                  <AssetCardList assets={pageItems} />
                </div>
                <div className="px-5 pb-4">
                  <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
                </div>
              </>
            ) : (
              <EmptyState icon={BarChart3} title="No assets found" description="Try a different filter or search term." />
            )}
          </Panel>

          <div className="hidden xl:block">
            <MarketDetailPanel symbol={selectedSymbol} />
          </div>
        </div>
      </PageContainer>
    </div>
  );
}

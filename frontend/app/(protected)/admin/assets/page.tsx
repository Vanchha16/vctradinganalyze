"use client";

import { useMemo, useState } from "react";

import { Coins, Plus } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader, Tag } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { AddAssetDialog } from "@/features/admin/components/add-asset-dialog";
import { AdminAssetFilterBar, type AdminAssetFilters } from "@/features/admin/components/asset-filter-bar";
import { AdminAssetTable, type AdminAssetSortKey } from "@/features/admin/components/asset-table";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { EditAssetDialog } from "@/features/admin/components/edit-asset-dialog";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useActivateAdminAsset, useDeactivateAdminAsset } from "@/hooks/use-admin-asset-actions";
import { useAdminAssets } from "@/hooks/use-admin-assets";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { Asset } from "@/services/types";

const DEFAULT_FILTERS: AdminAssetFilters = {
  search: undefined,
  market_type: undefined,
  is_active: undefined,
};

const PAGE_SIZE = 20;

/**
 * Admin Assets page (Phase 9F, ADR-138) - lets an admin control which
 * symbols the bot collects data for, analyses, and generates signals on.
 * `Asset.is_active` is the single control point for three production
 * pipelines (market data collection, hourly AI signal generation, news
 * matching) - deactivation is treated as a production-critical action,
 * not a cosmetic toggle, hence the explicit confirmation copy below.
 */
export default function AdminAssetsPage() {
  const [filters, setFilters] = useState<AdminAssetFilters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<AdminAssetSortKey>("symbol");
  const [order, setOrder] = useState<"asc" | "desc">("asc");

  const [addOpen, setAddOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
  const [statusTarget, setStatusTarget] = useState<Asset | null>(null);

  const assetsQuery = useAdminAssets({
    search: filters.search,
    market_type: filters.market_type,
    is_active: filters.is_active,
    page,
    limit: PAGE_SIZE,
  });
  const activateAsset = useActivateAdminAsset();
  const deactivateAsset = useDeactivateAdminAsset();

  const total = assetsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = useMemo(() => assetsQuery.data?.items ?? [], [assetsQuery.data]);

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const direction = order === "asc" ? 1 : -1;
      const aValue = a[sort as keyof Asset];
      const bValue = b[sort as keyof Asset];
      if (aValue === bValue) return 0;
      if (aValue === null) return 1;
      if (bValue === null) return -1;
      return aValue > bValue ? direction : -direction;
    });
  }, [items, sort, order]);

  function handleFilterChange(next: Partial<AdminAssetFilters>) {
    setFilters((prev) => ({ ...prev, ...next }));
    setPage(1);
  }

  function handleSortChange(key: AdminAssetSortKey) {
    if (key === sort) {
      setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setOrder("asc");
    }
  }

  async function handleToggleStatus() {
    if (!statusTarget) return;
    try {
      if (statusTarget.is_active) {
        await deactivateAsset.mutateAsync(statusTarget.id);
      } else {
        await activateAsset.mutateAsync(statusTarget.id);
      }
      toast.success(`${statusTarget.symbol} was ${statusTarget.is_active ? "deactivated" : "activated"}.`);
      setStatusTarget(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to update status.");
    }
  }

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Symbols"
          description="Control which symbols the bot collects data for, analyses, and generates signals on."
          actions={
            <Button onClick={() => setAddOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add symbol
            </Button>
          }
        />

        <AdminAssetFilterBar filters={filters} onChange={handleFilterChange} />

        <Panel>
          <PanelHeader
            title="All symbols"
            subtitle={`${total} symbol${total === 1 ? "" : "s"}`}
            icon={<Coins className="size-4" />}
            right={<Tag tone="brand">Live</Tag>}
          />
          {assetsQuery.isLoading ? (
            <div className="p-4">
              <Skeleton className="h-96 w-full" />
            </div>
          ) : assetsQuery.isError ? (
            <ErrorCard error={assetsQuery.error} onRetry={() => assetsQuery.refetch()} />
          ) : sortedItems.length > 0 ? (
            <>
              <AdminAssetTable
                assets={sortedItems}
                sort={sort}
                order={order}
                onSortChange={handleSortChange}
                onEdit={setEditingAsset}
                onToggleStatus={setStatusTarget}
              />
              <div className="px-5 pb-4">
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            </>
          ) : (
            <EmptyState icon={Coins} title="No symbols found" description="Try a different filter or search term." />
          )}
        </Panel>
      </PageContainer>

      <AddAssetDialog open={addOpen} onOpenChange={setAddOpen} />
      <EditAssetDialog
        asset={editingAsset}
        open={editingAsset !== null}
        onOpenChange={(open) => !open && setEditingAsset(null)}
      />
      <ConfirmActionDialog
        open={statusTarget !== null}
        onOpenChange={(open) => !open && setStatusTarget(null)}
        title={statusTarget?.is_active ? "Deactivate symbol?" : "Activate symbol?"}
        description={
          statusTarget?.is_active
            ? `${statusTarget?.symbol} will immediately stop: market data collection, AI signal generation, and news matching. Existing open signals for this symbol will still be monitored until they resolve.`
            : `${statusTarget?.symbol} will resume market data collection, AI signal generation, and news matching.`
        }
        actionLabel={statusTarget?.is_active ? "Deactivate" : "Activate"}
        variant={statusTarget?.is_active ? "destructive" : "default"}
        onConfirm={() => void handleToggleStatus()}
        isPending={activateAsset.isPending || deactivateAsset.isPending}
      />
    </div>
  );
}

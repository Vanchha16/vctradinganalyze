"use client";

import { Star } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { CardSkeleton } from "@/components/shared/skeletons";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { CreateWatchlistDialog } from "@/features/watchlists/components/create-watchlist-dialog";
import { RenameWatchlistDialog } from "@/features/watchlists/components/rename-watchlist-dialog";
import { WatchlistCard } from "@/features/watchlists/components/watchlist-card";
import { useDeleteWatchlist } from "@/hooks/use-watchlist-actions";
import { useWatchlists } from "@/hooks/use-watchlists";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { WatchlistSummaryResponse } from "@/services/types";

/** Real CRUD (docs/58 §2.4, Phase 7D-B) - replaces the ADR-103
 * `EmptyState`-only placeholder now that 7D-A's backend is live. */
export default function WatchlistsPage() {
  const watchlistsQuery = useWatchlists();
  const deleteWatchlist = useDeleteWatchlist();

  const [createOpen, setCreateOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<WatchlistSummaryResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<WatchlistSummaryResponse | null>(null);

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteWatchlist.mutateAsync(deleteTarget.id);
      toast.success("Watchlist deleted.");
      setDeleteTarget(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to delete watchlist.");
    }
  }

  const items = watchlistsQuery.data?.items ?? [];

  return (
    <div>
      <PageHeader
        title="Watchlists"
        description="Track your favorite assets in one place."
        actions={<Button onClick={() => setCreateOpen(true)}>New watchlist</Button>}
      />
      <PageContainer>
        {watchlistsQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <CardSkeleton key={index} />
            ))}
          </div>
        ) : watchlistsQuery.isError ? (
          <ErrorCard error={watchlistsQuery.error} onRetry={() => watchlistsQuery.refetch()} />
        ) : items.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {items.map((watchlist) => (
              <WatchlistCard
                key={watchlist.id}
                watchlist={watchlist}
                onRename={setRenameTarget}
                onDelete={setDeleteTarget}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Star}
            title="No watchlists yet"
            description="Create a watchlist to group and monitor the assets you care about most."
            action={<Button onClick={() => setCreateOpen(true)}>New watchlist</Button>}
          />
        )}
      </PageContainer>

      <CreateWatchlistDialog open={createOpen} onOpenChange={setCreateOpen} />
      <RenameWatchlistDialog
        watchlist={renameTarget}
        open={renameTarget !== null}
        onOpenChange={(open) => !open && setRenameTarget(null)}
      />
      <ConfirmActionDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete watchlist"
        description={`Are you sure you want to delete "${deleteTarget?.name}"? This cannot be undone.`}
        actionLabel="Delete"
        variant="destructive"
        onConfirm={() => void handleDelete()}
        isPending={deleteWatchlist.isPending}
      />
    </div>
  );
}

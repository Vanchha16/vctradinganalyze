"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { AddAssetDialog } from "@/features/watchlists/components/add-asset-dialog";
import { RenameWatchlistDialog } from "@/features/watchlists/components/rename-watchlist-dialog";
import { WatchlistDetail } from "@/features/watchlists/components/watchlist-detail";
import { useDeleteWatchlist, useRemoveWatchlistAsset } from "@/hooks/use-watchlist-actions";
import { useWatchlist } from "@/hooks/use-watchlist";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { Asset } from "@/services/types";

/** Detail view - add/remove assets (docs/58 §2.4, Phase 7D-B). A missing
 * or another user's watchlist id resolves to the same `resource_not_
 * found` 404 (docs/58 §2.2) - rendered via the shared `ErrorCard`, no
 * special-casing. */
export default function WatchlistDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const watchlistQuery = useWatchlist(params.id);
  const removeAsset = useRemoveWatchlistAsset();
  const deleteWatchlist = useDeleteWatchlist();

  const [renameOpen, setRenameOpen] = useState(false);
  const [addAssetOpen, setAddAssetOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  async function handleRemoveAsset(asset: Asset) {
    try {
      await removeAsset.mutateAsync({ id: params.id, assetId: asset.id });
      toast.success(`Removed ${asset.symbol} from watchlist.`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to remove asset.");
    }
  }

  async function handleDelete() {
    try {
      await deleteWatchlist.mutateAsync(params.id);
      toast.success("Watchlist deleted.");
      router.push("/watchlists");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to delete watchlist.");
    }
  }

  if (watchlistQuery.isLoading) {
    return (
      <div>
        <PageHeader title="Watchlist" />
        <PageContainer>
          <Skeleton className="h-96 w-full" />
        </PageContainer>
      </div>
    );
  }

  if (watchlistQuery.isError || !watchlistQuery.data) {
    return (
      <div>
        <PageHeader title="Watchlist" />
        <PageContainer>
          <ErrorCard error={watchlistQuery.error} onRetry={() => watchlistQuery.refetch()} />
        </PageContainer>
      </div>
    );
  }

  const watchlist = watchlistQuery.data;

  return (
    <div>
      <PageHeader
        title={watchlist.name}
        description={`${watchlist.assets.length} ${watchlist.assets.length === 1 ? "asset" : "assets"}`}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => router.push("/watchlists")}>
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Back
            </Button>
            <Button variant="outline" onClick={() => setRenameOpen(true)}>
              Rename
            </Button>
            <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
              Delete
            </Button>
            <Button onClick={() => setAddAssetOpen(true)}>Add asset</Button>
          </>
        }
      />
      <PageContainer>
        <WatchlistDetail
          assets={watchlist.assets}
          onRemove={(asset) => void handleRemoveAsset(asset)}
          onAddAsset={() => setAddAssetOpen(true)}
        />
      </PageContainer>

      <RenameWatchlistDialog
        watchlist={{ id: watchlist.id, name: watchlist.name }}
        open={renameOpen}
        onOpenChange={setRenameOpen}
      />
      <AddAssetDialog
        watchlistId={watchlist.id}
        existingAssetIds={watchlist.assets.map((asset) => asset.id)}
        open={addAssetOpen}
        onOpenChange={setAddAssetOpen}
      />
      <ConfirmActionDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete watchlist"
        description={`Are you sure you want to delete "${watchlist.name}"? This cannot be undone.`}
        actionLabel="Delete"
        variant="destructive"
        onConfirm={() => void handleDelete()}
        isPending={deleteWatchlist.isPending}
      />
    </div>
  );
}

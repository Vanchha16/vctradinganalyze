"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAssets } from "@/hooks/use-assets";
import { useAddWatchlistAsset } from "@/hooks/use-watchlist-actions";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";

/**
 * Asset picker reuses `useAssets()` - the same data source
 * `SymbolTimeframePicker` (`components/shared/symbol-timeframe-picker.tsx`)
 * already builds its Select from - rather than a new search component.
 * Already-added assets are filtered out client-side so a duplicate-add
 * attempt (409, docs/58 §2.2) can't even be selected in the first place;
 * the try/catch below still handles it gracefully in case of a race.
 */
export function AddAssetDialog({
  watchlistId,
  existingAssetIds,
  open,
  onOpenChange,
}: {
  watchlistId: string;
  existingAssetIds: string[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: assetsData, isLoading: assetsLoading } = useAssets();
  const addAsset = useAddWatchlistAsset();
  const [selectedAssetId, setSelectedAssetId] = useState<string | undefined>(undefined);

  const existing = new Set(existingAssetIds);
  const availableAssets = (assetsData?.items ?? []).filter((asset) => !existing.has(asset.id));

  async function handleAdd() {
    if (!selectedAssetId) return;
    try {
      await addAsset.mutateAsync({ id: watchlistId, payload: { asset_id: selectedAssetId } });
      toast.success("Asset added to watchlist.");
      setSelectedAssetId(undefined);
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to add asset.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add asset</DialogTitle>
          <DialogDescription>Choose an asset to add to this watchlist.</DialogDescription>
        </DialogHeader>
        <Select value={selectedAssetId} onValueChange={setSelectedAssetId} disabled={assetsLoading}>
          <SelectTrigger>
            <SelectValue
              placeholder={
                assetsLoading
                  ? "Loading..."
                  : availableAssets.length === 0
                    ? "All assets already added"
                    : "Select asset"
              }
            />
          </SelectTrigger>
          <SelectContent>
            {availableAssets.map((asset) => (
              <SelectItem key={asset.id} value={asset.id}>
                {asset.symbol} — {asset.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!selectedAssetId || addAsset.isPending}
            onClick={() => void handleAdd()}
          >
            {addAsset.isPending ? "Adding..." : "Add"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

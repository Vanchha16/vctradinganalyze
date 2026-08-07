"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useUpdateAdminAsset } from "@/hooks/use-admin-asset-actions";
import { formatEnumLabel } from "@/lib/format";
import { toast } from "@/lib/toast";
import { adminEditAssetSchema, type AdminEditAssetFormValues } from "@/lib/validation/admin";
import { ApiError } from "@/services/api-client";
import type { Asset, MarketType } from "@/services/types";

const MARKET_TYPES: MarketType[] = ["forex", "metal", "crypto", "index"];

/** `symbol` is deliberately not editable here - it is immutable after
 * creation (ADR-138). Mirrors `EditUserDialog` excluding `role`/
 * `is_active`/`password` for the same "single-purpose endpoint" reason. */
export function EditAssetDialog({
  asset,
  open,
  onOpenChange,
}: {
  asset: Asset | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const updateAsset = useUpdateAdminAsset();

  const form = useForm<AdminEditAssetFormValues>({
    resolver: zodResolver(adminEditAssetSchema),
    defaultValues: {
      name: "",
      market_type: "forex",
      exchange: "",
      base_currency: "",
      quote_currency: "",
    },
  });

  useEffect(() => {
    if (asset) {
      form.reset({
        name: asset.name,
        market_type: asset.market_type,
        exchange: asset.exchange ?? "",
        base_currency: asset.base_currency ?? "",
        quote_currency: asset.quote_currency ?? "",
      });
    }
  }, [asset, form]);

  async function onSubmit(values: AdminEditAssetFormValues) {
    if (!asset) return;
    try {
      await updateAsset.mutateAsync({
        id: asset.id,
        payload: {
          name: values.name,
          market_type: values.market_type,
          exchange: values.exchange || undefined,
          base_currency: values.base_currency || undefined,
          quote_currency: values.quote_currency || undefined,
        },
      });
      toast.success("Symbol updated.");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to update symbol.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit symbol</DialogTitle>
          <DialogDescription>
            Update {asset?.symbol}&rsquo;s details. Symbol itself cannot be changed.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="market_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Market Type</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {MARKET_TYPES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {formatEnumLabel(type)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="exchange"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Exchange (optional)</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="base_currency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Base currency (optional)</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="quote_currency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Quote currency (optional)</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Saving..." : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

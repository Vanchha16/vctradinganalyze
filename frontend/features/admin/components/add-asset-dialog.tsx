"use client";

import { zodResolver } from "@hookform/resolvers/zod";
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
import { useCreateAdminAsset } from "@/hooks/use-admin-asset-actions";
import { formatEnumLabel } from "@/lib/format";
import { toast } from "@/lib/toast";
import { adminCreateAssetSchema, type AdminCreateAssetFormValues } from "@/lib/validation/admin";
import { ApiError } from "@/services/api-client";
import type { MarketType } from "@/services/types";

const MARKET_TYPES: MarketType[] = ["forex", "metal", "crypto", "index"];

export function AddAssetDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createAsset = useCreateAdminAsset();

  const form = useForm<AdminCreateAssetFormValues>({
    resolver: zodResolver(adminCreateAssetSchema),
    defaultValues: {
      symbol: "",
      name: "",
      market_type: "forex",
      exchange: "",
      base_currency: "",
      quote_currency: "",
    },
  });

  function handleClose(next: boolean) {
    if (!next) form.reset();
    onOpenChange(next);
  }

  async function onSubmit(values: AdminCreateAssetFormValues) {
    try {
      const result = await createAsset.mutateAsync({
        symbol: values.symbol,
        name: values.name,
        market_type: values.market_type,
        exchange: values.exchange || undefined,
        base_currency: values.base_currency || undefined,
        quote_currency: values.quote_currency || undefined,
      });
      toast.success(`${result.symbol} was created.`);
      handleClose(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to create symbol.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add symbol</DialogTitle>
          <DialogDescription>
            Register a new tradable symbol. It starts active immediately.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <FormField
              control={form.control}
              name="symbol"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Symbol</FormLabel>
                  <FormControl>
                    <Input autoComplete="off" placeholder="EURUSD" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input autoComplete="off" placeholder="Euro / US Dollar" {...field} />
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
                    <Input autoComplete="off" {...field} />
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
                      <Input autoComplete="off" placeholder="EUR" {...field} />
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
                      <Input autoComplete="off" placeholder="USD" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => handleClose(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Creating..." : "Create symbol"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

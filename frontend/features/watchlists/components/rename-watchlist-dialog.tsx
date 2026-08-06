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
import { useRenameWatchlist } from "@/hooks/use-watchlist-actions";
import { toast } from "@/lib/toast";
import { watchlistNameSchema, type WatchlistNameFormValues } from "@/lib/validation/watchlists";
import { ApiError } from "@/services/api-client";

/** Takes only `{ id, name }` rather than a full watchlist response so the
 * same dialog works from both the list (`WatchlistSummaryResponse`) and
 * the detail page (`WatchlistDetailResponse`) without duplicating it. */
export function RenameWatchlistDialog({
  watchlist,
  open,
  onOpenChange,
}: {
  watchlist: { id: string; name: string } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const renameWatchlist = useRenameWatchlist();

  const form = useForm<WatchlistNameFormValues>({
    resolver: zodResolver(watchlistNameSchema),
    defaultValues: { name: "" },
  });

  useEffect(() => {
    if (watchlist) form.reset({ name: watchlist.name });
  }, [watchlist, form]);

  async function onSubmit(values: WatchlistNameFormValues) {
    if (!watchlist) return;
    try {
      await renameWatchlist.mutateAsync({ id: watchlist.id, payload: { name: values.name } });
      toast.success("Watchlist renamed.");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to rename watchlist.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rename watchlist</DialogTitle>
          <DialogDescription>Choose a new name for &ldquo;{watchlist?.name}&rdquo;.</DialogDescription>
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
                    <Input autoFocus {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Saving..." : "Save"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

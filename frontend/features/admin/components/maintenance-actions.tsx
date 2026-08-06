"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { useRefreshCalendar, useRefreshNews } from "@/hooks/use-admin-maintenance-actions";
import { toast } from "@/lib/toast";

type ConfirmingAction = "news" | "calendar" | null;

/**
 * The two `POST /admin/maintenance` actions docs/58 §3.3 actually has an
 * implementation for - "No maintenance-action buttons beyond" these two.
 * Placed on System Health (the operational liveness page) rather than
 * Settings, since it already shows today's activity these actions affect.
 *
 * Safety requirements (Phase 7D-D spec §4, all load-bearing, not
 * decorative): confirm before firing via the existing
 * `ConfirmActionDialog` (never a new confirmation), copy that states the
 * real consequence (a live vendor call, real quota), the trigger button
 * disabled for the whole in-flight duration (not just while the dialog is
 * open), and a client-side timeout (`use-admin-maintenance-actions.ts`)
 * so a hung request can't leave the button disabled forever - the backend
 * runs both ingestions synchronously and inline (ADR-130).
 */
export function MaintenanceActionsPanel() {
  const [confirming, setConfirming] = useState<ConfirmingAction>(null);
  const refreshNews = useRefreshNews();
  const refreshCalendar = useRefreshCalendar();

  async function handleConfirmNews() {
    try {
      const result = await refreshNews.mutateAsync();
      const count = result.articles_ingested;
      toast.success(`News refreshed - ${count} new article${count === 1 ? "" : "s"} ingested.`);
      setConfirming(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to refresh news.");
    }
  }

  async function handleConfirmCalendar() {
    try {
      const result = await refreshCalendar.mutateAsync();
      const calendar = result.calendar;
      toast.success(
        calendar
          ? `Calendar refreshed - ${calendar.events_created} created, ${calendar.events_updated} updated.`
          : "Calendar refreshed.",
      );
      setConfirming(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to refresh calendar.");
    }
  }

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          onClick={() => setConfirming("news")}
          disabled={refreshNews.isPending}
        >
          {refreshNews.isPending ? "Refreshing News…" : "Refresh News"}
        </Button>
        <Button
          variant="outline"
          onClick={() => setConfirming("calendar")}
          disabled={refreshCalendar.isPending}
        >
          {refreshCalendar.isPending ? "Refreshing Calendar…" : "Refresh Calendar"}
        </Button>
      </div>

      <ConfirmActionDialog
        open={confirming === "news"}
        onOpenChange={(open) => !open && setConfirming(null)}
        title="Refresh news now?"
        description="This immediately calls the configured news provider to fetch the latest articles and may consume real vendor API quota. It runs synchronously and can take several seconds."
        actionLabel="Refresh News"
        onConfirm={() => void handleConfirmNews()}
        isPending={refreshNews.isPending}
      />
      <ConfirmActionDialog
        open={confirming === "calendar"}
        onOpenChange={(open) => !open && setConfirming(null)}
        title="Refresh economic calendar now?"
        description="This immediately calls the configured economic calendar provider to fetch the latest events and may consume real vendor API quota. It runs synchronously and can take several seconds."
        actionLabel="Refresh Calendar"
        onConfirm={() => void handleConfirmCalendar()}
        isPending={refreshCalendar.isPending}
      />
    </>
  );
}

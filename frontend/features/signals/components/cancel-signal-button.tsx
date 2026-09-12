"use client";

import { Ban } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { useCancelSignal } from "@/hooks/use-cancel-signal";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { SignalResponse } from "@/services/types";

/**
 * ADR-169 - shown to the super admin only (the API enforces that too), and
 * only for a draft or an unfilled signal. A live trade is not offered:
 * cancelling the signal would not close the trade in MT5.
 */
export function CancelSignalButton({ signal }: { signal: SignalResponse }) {
  const [open, setOpen] = useState(false);
  const cancel = useCancelSignal();

  if (signal.status !== "draft" && signal.status !== "active") return null;
  const published = signal.status === "active";

  async function handleConfirm() {
    try {
      await cancel.mutateAsync(signal.id);
      setOpen(false);
      toast.success("Signal cancelled.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Something went wrong.");
    }
  }

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>
        <Ban className="mr-2 h-4 w-4" />
        Cancel signal
      </Button>
      <ConfirmActionDialog
        open={open}
        onOpenChange={setOpen}
        title="Cancel this signal?"
        description={
          published
            ? "The EA deletes its pending order on its next check, and Telegram subscribers are told the signal is cancelled. This cannot be undone."
            : "This draft has not been sent to anyone, and it will not be published. This cannot be undone."
        }
        actionLabel="Cancel signal"
        variant="destructive"
        onConfirm={() => void handleConfirm()}
        isPending={cancel.isPending}
      />
    </>
  );
}

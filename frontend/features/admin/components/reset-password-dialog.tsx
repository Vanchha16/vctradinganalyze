"use client";

import { useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { TemporaryPasswordReveal } from "@/features/admin/components/temporary-password-reveal";
import { useResetAdminUserPassword } from "@/hooks/use-admin-user-actions";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { AdminUserResponse } from "@/services/types";

/**
 * Two-step dialog: confirm, then reveal the generated password exactly
 * once (docs/59 §6.2 - `POST /admin/users/{id}/reset-password` returns it
 * only in that one response body, never retrievable again).
 */
export function ResetPasswordDialog({
  user,
  open,
  onOpenChange,
}: {
  user: AdminUserResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const resetPassword = useResetAdminUserPassword();
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);

  function handleClose(next: boolean) {
    if (!next) setTemporaryPassword(null);
    onOpenChange(next);
  }

  async function handleConfirm() {
    if (!user) return;
    try {
      const result = await resetPassword.mutateAsync(user.id);
      setTemporaryPassword(result.temporary_password);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to reset password.");
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={handleClose}>
      <AlertDialogContent>
        {temporaryPassword ? (
          <>
            <AlertDialogHeader>
              <AlertDialogTitle>Password reset</AlertDialogTitle>
              <AlertDialogDescription>
                {user?.username}&rsquo;s password has been reset. Every existing session for this
                account has been revoked.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <TemporaryPasswordReveal password={temporaryPassword} />
            <AlertDialogFooter>
              <Button onClick={() => handleClose(false)}>Done</Button>
            </AlertDialogFooter>
          </>
        ) : (
          <>
            <AlertDialogHeader>
              <AlertDialogTitle>Reset password?</AlertDialogTitle>
              <AlertDialogDescription>
                This generates a new temporary password for <strong>{user?.username}</strong> and
                signs them out of every active session. They&rsquo;ll be required to change it on
                next login.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={resetPassword.isPending}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                disabled={resetPassword.isPending}
                onClick={(event) => {
                  event.preventDefault();
                  void handleConfirm();
                }}
              >
                {resetPassword.isPending ? "Resetting..." : "Reset Password"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </>
        )}
      </AlertDialogContent>
    </AlertDialog>
  );
}
